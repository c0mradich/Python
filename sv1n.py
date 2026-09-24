import socket
import threading
import argparse

HOST = "0.0.0.0"
BUFFER_SIZE = 4096

clients = {}
clients_lock = threading.Lock()


def broadcast(message, sender=None):
    data = message.encode("utf-8")

    with clients_lock:
        for client in list(clients.values()):
            if client is not sender:
                try:
                    client.sendall(data)
                except OSError:
                    pass


def remove_client(username):
    with clients_lock:
        client = clients.pop(username, None)

    if client:
        try:
            client.close()
        except OSError:
            pass

    print(f"[-] {username} disconnected")


def handle_client(client, username):
    print(f"[+] {username} connected")
    broadcast(f"[SERVER] {username} joined the chat.\n", client)

    try:
        while True:
            data = client.recv(BUFFER_SIZE)

            if not data:
                break

            message = data.decode("utf-8", errors="replace").strip()

            if not message:
                continue

            if message == "/users":
                with clients_lock:
                    users = ", ".join(clients.keys())

                client.sendall(
                    f"[SERVER] Online users: {users}\n".encode("utf-8")
                )
                continue

            if message == "/quit":
                break

            formatted = f"{username}: {message}\n"
            print(formatted, end="")
            broadcast(formatted, client)

    except ConnectionError:
        pass
    finally:
        remove_client(username)
        broadcast(f"[SERVER] {username} left the chat.\n")


def run_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, port))
    server.listen(10)

    print(f"[SERVER] Listening on {HOST}:{port}")

    try:
        while True:
            client, address = server.accept()

            client.sendall(b"NAME\n")
            name_data = client.recv(128)

            if not name_data:
                client.close()
                continue

            username = name_data.decode("utf-8", errors="replace").strip()

            if not username or len(username) > 20:
                client.sendall(b"[SERVER] Invalid username.\n")
                client.close()
                continue

            with clients_lock:
                if username in clients:
                    client.sendall(b"[SERVER] Username already in use.\n")
                    client.close()
                    continue

                clients[username] = client

            thread = threading.Thread(
                target=handle_client,
                args=(client, username),
                daemon=True
            )
            thread.start()

    except KeyboardInterrupt:
        print("\n[SERVER] Stopped.")
    finally:
        with clients_lock:
            for client in clients.values():
                try:
                    client.close()
                except OSError:
                    pass

        server.close()


def receive_messages(client):
    try:
        while True:
            data = client.recv(BUFFER_SIZE)

            if not data:
                print("\n[SERVER] Connection closed.")
                break

            print(data.decode("utf-8", errors="replace"), end="")

    except (ConnectionError, OSError):
        print("\n[SERVER] Connection lost.")


def run_client(target, port, username):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect((target, port))
        client.sendall(username.encode("utf-8"))

    except OSError as error:
        print(f"[ERROR] Could not connect: {error}")
        return

    print(f"[CONNECTED] {target}:{port}")
    print("Commands: /users, /quit")

    receiver = threading.Thread(
        target=receive_messages,
        args=(client,),
        daemon=True
    )
    receiver.start()

    try:
        while True:
            message = input("> ").strip()

            if not message:
                continue

            client.sendall(message.encode("utf-8"))

            if message == "/quit":
                break

    except (KeyboardInterrupt, OSError):
        pass
    finally:
        try:
            client.close()
        except OSError:
            pass

        print("[CLIENT] Stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="SV1N Safe TCP Chat"
    )

    parser.add_argument(
        "--name",
        help="Username for client mode"
    )

    parser.add_argument(
        "-l",
        "--listen",
        action="store_true",
        help="Start server"
    )

    parser.add_argument(
        "-t",
        "--target",
        help="Server IP address"
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="TCP port (default: 8000)"
    )

    args = parser.parse_args()

    if args.listen:
        run_server(args.port)
        return

    if not args.name:
        parser.error("--name is required in client mode")

    if not args.target:
        parser.error("--target is required in client mode")

    if len(args.name) > 20:
        parser.error("Username must be 20 characters or shorter")

    run_client(args.target, args.port, args.name)


if __name__ == "__main__":
    main()
