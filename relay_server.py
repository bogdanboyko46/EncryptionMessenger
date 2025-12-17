import socket
import threading

HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 5000        # Port clients will connect to

clients = []       # List of connected client sockets
lock = threading.Lock()


def handle_client(conn, addr):
    print(f"[+] Connected: {addr}")

    with lock:
        clients.append(conn)

    try:
        while True:
            data = conn.recv(4096)
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
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"[+] Relay server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True
        )
        thread.start()


if __name__ == "__main__":
    main()
