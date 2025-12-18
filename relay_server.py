import socket

# we need threading to stop multiple clients using same function anyway
import threading

from protocol import send_message, recv_message

HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 5000        # Port clients will connect to

clients = dict()       # List of connected client sockets
lock = threading.Lock()

clients: dict[str, socket.socket] = dict()  # maps client names to their sockets
socket_to_name: dict[socket.socket, str] = dict()  # maps sockets to client names
sender_choice: dict[socket.socket, str] = dict()  # maps sockets to the name of the client they want to connect to
# protect shared data

lock = threading.Lock()

# Every client will thats connected to the relay server will have an instance of this (the instance is hosted here ofc)
def handle_client(conn, addr, name):
    # prints the ip address of the client that connects to the relay
    print(f"[+] Connected: {addr}")

    # if 2 clients try connect at same time the lock makes sure each action happens 1 after the other
    with lock:

        if clients[name]:
            # name already taken
            conn.sendall(b"Name already taken. Disconnecting.")
            conn.close()
            return
            

    while True:
        msg = recv_message(conn)

        
            


def main():
    # This creates a tcp socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bypasses "Address already in use" error
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Incoming traffic requests get sent to server
    server.bind((HOST, PORT))
    # Socket is now listening (bascially open to requests)
    server.listen()

    print(f"[+] Relay server listening on {HOST}:{PORT}")

    # Loop running forever waiting for clients
    while True:
        # Code pauses here until client tries connecting
        conn, addr, name = server.accept()
        # Creates a new thread that will run the handle_client function
        thread = threading.Thread(
            target=handle_client,
            args=(conn, addr, name),
            # daemon means it will exit automatically
            daemon=True
        )
        thread.start()


if __name__ == "__main__":
    main()

    
