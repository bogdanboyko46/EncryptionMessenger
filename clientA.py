import socket
from protocol import send_message, recv_message


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("72.62.81.113", 5000))

user_name = input("Enter your name: ")
while True:
    msg = input("> ")
    if not msg:
        continue
    
    send_message(s, user_name, msg)

