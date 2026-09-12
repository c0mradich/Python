import threading
import socket
import subprocess


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("localhost", 5000))

clients = {}

def client_listener(client, username):
    while True:
        try:

            data = client.recv(1024)

            if not data:
                print("Client disconnected")
                del clients[username]
                client.close()
                break

            data = data.decode("UTF-8", errors="ignore")

            # DYBUG: print(data)
            if data == "exit\n":
                del clients[username]
                client.close()
                break


            datavalue = data.split("> ")[1]
            #print (f"Received from {username}: {datavalue}")

            if datavalue.startswith("CMD_OUTPUT"):

                priority = datavalue.split(" ")[1]
                #print(f"Priority: {priority}")

                output = " ".join(data.split(" ")[3:])
                #print(f"Output: {output}")
                #print("DATA: ", data)

                prioritySocket = clients.get(priority)
                if prioritySocket:
                    try:
                        #print("SENDING: ", f"{username}> {output}\n")
                        prioritySocket.send(f"{username}> {output}\n".encode("UTF-8"))
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

            else:
                data = data.encode("UTF-8")
                for connected_client in clients.values():
                    #print("Sending to:", connected_client)
                    connected_client.sendall(data + b"\n")

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

