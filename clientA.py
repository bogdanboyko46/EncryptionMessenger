import socket
from protocol import send_message, recv_message

import inspect
print("send_message is:", send_message)
print("send_message signature:", inspect.signature(send_message))
print("protocol module file:", inspect.getfile(send_message))

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("72.62.81.113", 5000))

# strip whitespace from user inputs
user = input("Enter your name: ").strip()
to_connect = input("Enter the name of the person you want to connect to: ").strip()

# "type" denotes the type of message being sent, in this case being a registration message
send_message(s, {"type": "REGISTER", "name": user})
# prints this message to confirm registration
print(recv_message(s))

while True:
    msg = input("> ")
    if not msg:
        continue
    
    # the type is a SEND message, that will be sent to the other user
    send_message(s, {
        "type": "SEND", 
        "to": to_connect, 
        "message": msg
    })
