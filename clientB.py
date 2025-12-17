import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", 5000))

while True:
    data = s.recv(4096)
    if not data:
        print("Disconnected")
        break
    print("Received:", data.decode())
