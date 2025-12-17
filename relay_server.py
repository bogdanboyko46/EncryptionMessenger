import socket

# we need threading to stop multiple clients using same function anyway
import threading

HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 5000        # Port clients will connect to

clients = []       # List of connected client sockets
lock = threading.Lock()

# Every client will thats connected to the relay server will have an instance of this (the instance is hosted here ofc)
def handle_client(conn, addr):
    # prints the ip address of the client that connects to the relay
    print(f"[+] Connected: {addr}")

    # if 2 clients try connect at same time the lock makes sure each action happens 1 after the other
    with lock:
        # adds socket to client list
        clients.append(conn)

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
                for client in clients:
                    if client != conn:
                        client.sendall(data)

    except Exception as e:
        print(f"[!] Error with {addr}: {e}")

    finally:
        print(f"[-] Disconnected: {addr}")
        with lock:
            clients.remove(conn)
        conn.close()


def main():
    # This creates a tcp socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Incoming traffic requests get sent to server
    server.bind((HOST, PORT))
    # Socket is now listening (bascially open to requests)
    server.listen()

    print(f"[+] Relay server listening on {HOST}:{PORT}")

    # Loop running forever waiting for clients
    while True:
        # Code pauses here until client tries connecting
        conn, addr = server.accept()
        # Creates a new thread that will run the handle_client function
        thread = threading.Thread(
            target=handle_client,
            args=(conn, addr),
            # daemon means it will exit automatically
            daemon=True
        )
        thread.start()


if __name__ == "__main__":
    main()
