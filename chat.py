import threading
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("localhost", 5000))

clients = {}

def client_listener(client, username):
    while True:
        try:

            data = client.recv(4096)

            if not data:
                print("Client disconnected")
                del clients[username]
                client.close()
                break

            data = data.decode("UTF-8", errors="ignore")

            if data == "exit":
                del clients[username]
                client.close()
                break

            print(data)

            data = data.encode("UTF-8")
            for connected_client in clients.values():
                print("Sending to:", connected_client)
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
    clients[username] = client

    print(f"Connection from {addr} has been established!")

    listener = threading.Thread(
        target=client_listener,
        args=(client, username),
        daemon=True
    )

    listener.start()

