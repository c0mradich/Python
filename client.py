import socket
import sys
import threading
import argparse

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
            s.send(cmd.encode("UTF-8"))
            break
        cmd = name + cmd

        s.send(cmd.encode("UTF-8"))

def client_listener():
    while True:
        try:
            data = s.recv(4096)

            # print(f"\n[RECEIVED] {data!r}")

            if not data:
                break

            data = data.decode("UTF-8", errors="ignore")
            dataname = data.split(">")[0]
            if dataname != name[:-2]:
                print(f"\n{data}")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            break

thread = threading.Thread(target=client_listener)
thread2 = threading.Thread(target=client_sender)

thread.start()
thread2.start()