import socket
from protocol import send_message, recv_message

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("72.62.81.113", 5000))

user = input("Enter your name: ").strip()
to_connect = input("Enter the name of the person you want to connect to: ").strip()

# same as clienA file, it is a registration message
send_message(s, {"type": "REGISTER", "name": user})
print(recv_message(s))

while True:
    msg = recv_message(s)

    if not msg:
        break
    # it will receive a msg but checks if its type is MSG
    if msg.get("type") == "MSG":
        print(f"{msg.get('from')}: {msg.get('message')}")
    else:
        print(f"Unknown message type received, attempted: {msg}")
