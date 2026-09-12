import threading
import socket
import os


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("localhost", 5000))

clients = {}

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


def receive_cmd_output(client, val):
    buffer = val.encode("UTF-8")

    if b"CMD_OUTPUT_END\n" not in buffer:
        while b"CMD_OUTPUT_END\n" not in buffer:
            chunk = client.recv(1024)

            if not chunk:
                raise ConnectionError("Client disconnected during CMD_OUTPUT")

            buffer += chunk
    return buffer.decode("UTF-8", errors="ignore")

def client_listener(client, username):
    while True:
        try:

            data = client.recv(1024)
            buffer = data
            if not data:
                print("Client disconnected")
                del clients[username]
                client.close()
                break

            elif b"FILE_TRANSFER" in buffer:
                header_end = buffer.find(b"\n")

                if header_end == -1:
                    print("Incomplete FILE_TRANSFER header")
                    continue

                header = buffer[:header_end]
                first_file_data = buffer[header_end + 1:]

                parts = header.decode("UTF-8").split(" ", 4)

                if len(parts) != 5:
                    print("Invalid FILE_TRANSFER header:", header)
                    continue

                filename = parts[1]
                priorityname = parts[3]
                file_size = int(parts[4])

                #print("FILE_TRANSFER DETECTED:",filename,"FROM:",priorityname,"SIZE:",file_size)

                target = clients.get(priorityname)

                if not target:
                    print(f"Client {priorityname} not found.")
                    continue

                #print(f"Receiving {filename} from {username}")

                receive_file(
                    client,
                    first_file_data,
                    filename,
                    file_size
                )

                #print(f"Sending {filename} to {priorityname}")

                file_sender(target, filename)

                continue

            data = data.decode("UTF-8", errors="ignore")

            #print(data)
            if data == "exit\n":
                del clients[username]
                client.close()
                break


            datavalue = data.split("> ")[1]
            #print (f"Received from {username}: {datavalue}")

            if datavalue.startswith("CMD_OUTPUT"):

                data = receive_cmd_output(client, data)
                parts = data.split(" ", 2)
                priority = parts[2].split(" ")[0]
                print(priority)
                output = " ".join(data.split(" ")[5:])

                prioritySocket = clients.get(priority)
                print(prioritySocket)

                if prioritySocket:
                    try:
                        prioritySocket.send(
                            f"{username}> {output}\n".encode("UTF-8")
                        )
                        continue

                    except Exception as e:
                        print(f"Failed to send output to {priority}: {e}")

            
            if datavalue.startswith("run"):
                dataparamount = data.split("run")[1].strip()

                #print(f"dataparamount: {dataparamount}")

                if dataparamount == "":
                    print("No command provided to run.")
                    client.send(f"No command provided to run.\n".encode("UTF-8"))
                    continue

                captivename = data.split(" ")[2].strip()                
                #print(f"Executing command from {captivename}: {datavalue.split(captivename + " ")[1]}")
                command = datavalue.split(captivename + " ")[1].strip()
                if command == "":
                    print("No command provided to run.")
                    client.send(f"No command provided to run.\n".encode("UTF-8"))
                    continue

                #print(f"Command to execute: {command}")
                captive = clients.get(captivename)
                if captive:
                    try:
                        captive.send(f"{username} -run {command}\n".encode("UTF-8"))
                        continue
                    except Exception as e:
                        print(f"Failed to send command to {captivename}: {e}")
                else:
                    print(f"Client {captivename} not found.")
                    client.send(f"Client {captivename} not found.\n".encode("UTF-8"))

            elif datavalue.startswith("get"):
                filename = datavalue.split("get ")[1].strip()
                captivename = data.split(" ")[2].strip()
                captive = clients.get(captivename)
                if filename == "":
                    print("No filename provided to get.")
                    client.send(f"No filename provided to get.\n".encode("UTF-8"))
                    continue

                #print(f"Sending file {filename} to {username}")
                if captive:
                    try:
                        captive.send(f"{username} -get {filename}\n".encode("UTF-8"))
                        continue
                    except Exception as e:
                        print(f"Failed to send get request to {captivename}: {e}")
                continue
            
            else:
                data = data.encode("UTF-8")
                for connected_client in clients.values():
                    #print("Sending to:", connected_client, "DATA: ", data.decode("UTF-8", errors="ignore"))
                    connected_client.sendall(data)

        except Exception as e:
            print(f"ERROR: {e}")

            if username in clients:
                del clients[username]

            client.close()
            break

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

