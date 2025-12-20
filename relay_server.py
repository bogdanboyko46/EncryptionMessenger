import socket

# we need threading to stop multiple clients using same function anyway
import threading

from protocol import send_message, recv_message

HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 5000        # Port clients will connect to

clients = dict()      # List of connected client sockets
lock = threading.Lock()

# Every client will thats connected to the relay server will have an instance of this (the instance is hosted here ofc)
def handle_client(conn, addr):
    # prints the ip address of the client that connects to the relay
    print(f"[+] Connected: {addr}")

    msg = recv_message(conn)
    
    name = msg.get("name").strip()
    
    # if 2 clients try connect at same time the lock makes sure each action happens 1 after the other
    with lock:
        
        # checks if the name is already taken, gives an "ERROR" type message
        if name in clients:
            send_message(conn, {"type": "ERROR", "message": "Name already taken"})
            conn.close()
            return
        
        # otherwise adds the client to the clients dict
        clients[name] = conn

        # sends a confirmation message back to the client
        send_message(conn, {"type": "REGISTERED", "text": f"Registered as {name}"})
        print(f"[+] User registered: {name} from {addr}")

        while True:
            # msg recieved from client
            msg = recv_message(conn)

            if not msg:
                break
            
            # checks if the type is SEND
            if msg.get("type") == "SEND":
                to = msg.get("to")
                txt = msg.get("message")

                with lock:
                    target_conn = clients.get(to)
                # if target_conn not null, then send a message to that connection
                if target_conn:
                    send_message(target_conn, {"type": "MSG", "from": name, "message": txt})
                else:
                    send_message(conn, {"type": "ERROR", "message": f"User {to} not found"})
        
        # client disconnected, remove from clients dict
        print(f"[-] Disconnected: {addr}")
        with lock:
            if clients.get(name) == conn:
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
    print("[+] Waiting for clients to connect...")

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

    
