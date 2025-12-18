import socket
from protocol import send_message, recv_message

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("72.62.81.113", 5000))

user = input("Enter your name: ")
to_connect = input("Enter the name of the person you want to connect to: ")

while True:
    data = s.recv(4096)
    if not data:
        print("Disconnected")
        break
    print(data.decode())
