import socket
from threading import Thread

class Server:
    Client = []
    def __init__(self, HOST, PORT):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((HOST, PORT))
        self.socket.listen(5)
        print("Waiting for connection...")

    def listen(self):
        while True:
            client_socket, address = self.socket.accept()
            print("Connection from: " + str(address))

            client_name = client_socket.recv(1024).decode()
            client = {'client_name': client_name, 'client_socket': client_socket}

            self.broadcast_message(client_name, client_name + " has join the chat!")

            self.Client.append(client)
            Thread(target=self.handle_new_client, args=(client,)).start()
    
    def handle_new_client(self, client):
        client_name = client["client_name"]
        client_socket = client["client_socket"]

        while True:
            client_message = client_socket.recv(1024).decode()

            if client_message.strip() == client_name + ": bye" or not client_message.strip():
                self.broadcast_message(client_name, client_name + " has left the chat!")
                self.Client.remove(client)
                client_socket.close()
                break
            else:
                self.broadcast_message(client_name, client_message)

    def broadcast_message(self, sender, message):
        for client in self.Client:
            client_name = client["client_name"]
            client_socket = client["client_socket"]
            if client_name != sender:
                client_socket.send(message.encode())

if __name__ == "__main__":
    server = Server("127.0.0.1", 9000)
    server.listen()