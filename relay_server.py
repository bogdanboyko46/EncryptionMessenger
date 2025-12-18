import socket

# we need threading to stop multiple clients using same function anyway
import threading

from protocol import send_message, recv_message

HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 5000        # Port clients will connect to

clients = dict()       # List of connected client sockets
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
        
        # maps to name of client to instance of socket
        clients[name] = conn

    try:
        # waiting to recieve bytes from the client
        while True:
            # The instance will pause here and wait to recieve data from the client
            # The code wont go past this line until its recieved the data from the conn.recv() call
            data = conn.recv(4096)
            # basically just checks if the client disconnected
            if not data:
                break  # client disconnected

            # Relay the data to all other clients
            with lock:
                for name in clients:
                    if clients[name] != conn:
                        clients[name].sendall(data)

    except Exception as e:
        print(f"[!] Error with {addr}: {e}")

    finally:
        print(f"[-] Disconnected: {addr}")
        with lock:
            del clients[name]
        conn.close()


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

clients: dict[str, socket.socket] = dict()  # List of connected client sockets
# sockets mapped to names
socket_to_name: dict[socket.socket, str] = dict()
# receiver_socket -> allowed sender usernames
allowed_senders: dict[socket.socket, set[str]] = dict()
# protect shared data
lock = threading.Lock()

def safe_send(sock: socket.socket, message: dict):
    try:
        send_message(sock, message)
    except Exception as e:
        print(f"[!] Error sending to {socket_to_name.get(sock, 'unknown')}: {e}")


def disconnect(sock: socket.socket):
    with lock:
        name = socket_to_name.get(sock, "unknown")
        
        allowed_senders.pop(sock, None)

        if name is not None and name in clients:
            del clients[name]
    
    try:
        sock.close()
    except Exception as e:
        print(f"[!] Error closing socket for {name}: {e}")