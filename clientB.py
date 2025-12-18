import socket
from protocol import send_message, recv_message

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("72.62.81.113", 5000))

while True:
    data = s.recv(4096)
    if not data:
        print("Disconnected")
        break
    print("Received:", data.decode())
