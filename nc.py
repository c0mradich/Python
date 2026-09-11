#!/usr/bin/env python3

import sys
import socket
import getopt
import threading
import subprocess


# Глобальные переменные
listen = False
command = False
upload = False

execute = ""
target = ""
upload_destination = ""
port = 0


def usage():
    print("BHP Net Tool")
    print()
    print("Usage: netcat.py -t target_host -p port")
    print("-l --listen              - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run - execute the given file upon receiving a connection")
    print("-c --command             - initialize a command shell")
    print("-u --upload=destination  - upon receiving connection upload a file and write to [destination]")
    print()

    print("Examples:")
    print("netcat.py -t 192.168.0.1 -p 5555 -l -c")
    print("netcat.py -t 192.168.0.1 -p 5555 -l -u=/target.exe")
    print("netcat.py -t 192.168.0.1 -p 5555 -l -e='cat /etc/passwd'")
    print("echo 'Hello' | ./netcat.py -t 192.168.11.12 -p 135")

    sys.exit(0)


def run_command(command):
    """
    Выполняет команду через shell
    и возвращает результат в виде bytes.
    """

    command = command.strip()

    if not command:
        return b"\n"

    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            shell=True
        )

    except Exception:
        output = b"Failed to execute command.\n"

    if not output.endswith(b"\n"):
        output += b"\n"

    return output


def client_listener(client):
    """
    Отдельный поток для непрерывного
    чтения данных от сервера.
    """

    while True:
        try:
            data = client.recv(4096)

            if not data:
                break

            print(
                data.decode("latin1", errors="ignore"),
                end=""
            )

        except Exception:
            break


def client_sender(buffer):
    """
    Подключается к серверу и позволяет
    пользователю отправлять команды.
    """

    client = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    try:
        client.connect((target, port))

        # Отправляем первоначальный buffer,
        # если он существует.
        if buffer:
            client.send(buffer)

        # Запускаем отдельный поток,
        # который слушает ответы сервера.
        listener = threading.Thread(
            target=client_listener,
            args=(client,),
            daemon=True
        )

        listener.start()

        # Основной поток читает команды пользователя.
        while True:
            cmd = input()

            client.send(
                cmd.encode() + b"\n"
            )

    except Exception as e:
        print(f"[*] Exception! {e}")

    finally:
        client.close()


def client_handler(client_socket):
    """
    Обрабатывает подключившегося клиента.
    """

    global upload_destination
    global execute
    global command

    # --------------------------------------------------
    # Upload mode
    # --------------------------------------------------

    if upload_destination:
        file_buffer = b""

        while True:
            data = client_socket.recv(1024)

            if not data:
                break

            file_buffer += data

        try:
            with open(upload_destination, "wb") as f:
                f.write(file_buffer)

            client_socket.send(
                f"Successfully saved to {upload_destination}\n".encode()
            )

        except Exception:
            client_socket.send(
                b"Failed to save file.\n"
            )

    # --------------------------------------------------
    # Execute mode
    # --------------------------------------------------

    if execute:
        output = run_command(execute)

        client_socket.send(output)

    # --------------------------------------------------
    # Command shell mode
    # --------------------------------------------------

    if command:

        while True:

            client_socket.send(
                b"<BHP:#> "
            )

            cmd_buffer = b""

            # Получаем команду до символа \n
            while b"\n" not in cmd_buffer:

                chunk = client_socket.recv(1024)

                if not chunk:
                    break

                cmd_buffer += chunk

            cmd = cmd_buffer.decode(
                "latin1",
                errors="ignore"
            ).strip()

            if cmd:
                response = run_command(cmd)

                client_socket.send(response)


def server_loop():
    """
    Создаёт TCP-сервер и принимает
    входящие подключения.
    """

    global target

    if not target:
        target = "0.0.0.0"

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.bind(
        (target, port)
    )

    server.listen(5)

    print(
        f"[*] Listening on {target}:{port}"
    )

    while True:

        client_socket, addr = server.accept()

        print(
            f"[*] Incoming connection from "
            f"{addr[0]}:{addr[1]}"
        )

        # Для каждого клиента создаём отдельный поток.
        client_thread = threading.Thread(
            target=client_handler,
            args=(client_socket,)
        )

        client_thread.start()


def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target

    if not len(sys.argv[1:]):
        usage()

    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hle:t:p:cu:",
            [
                "help",
                "listen",
                "execute",
                "target",
                "port",
                "command",
                "upload"
            ]
        )

    except getopt.GetoptError as err:
        print(str(err))
        usage()

    # Обрабатываем аргументы командной строки.
    for option, argument in opts:

        if option in ("-h", "--help"):
            usage()

        elif option in ("-l", "--listen"):
            listen = True

        elif option in ("-e", "--execute"):
            execute = argument

        elif option in ("-c", "--command"):
            command = True

        elif option in ("-u", "--upload"):
            upload_destination = argument

        elif option in ("-t", "--target"):
            target = argument

        elif option in ("-p", "--port"):
            port = int(argument)

    # --------------------------------------------------
    # Client
    # --------------------------------------------------

    if not listen and target and port > 0:

        buffer = sys.stdin.buffer.read()

        client_sender(buffer)

    # --------------------------------------------------
    # Server
    # --------------------------------------------------

    if listen:
        server_loop()


if __name__ == "__main__":
    main()