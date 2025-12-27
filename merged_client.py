import socket
import threading
from protocol import recv_message, send_message

def create_room(socket, room_name, owner):
    send_message(socket, {"TYPE": "CREATE_ROOM", "ROOM_NAME": room_name, "OWNER": owner})

def join_room(socket, room_name, rooms_dict):
    send_message(socket, {"TYPE": "JOIN_ROOM", "ROOM_NAME": room_name})

def reciever_loop(s: socket.socket):
    while True:
        msg = recv_message(s)

        if msg is None:
            print("Server disconnected. Exiting...")
            break
            
        if msg.get("TYPE") == "RECIEVE":
            print(f"{msg["FROM"]}: {msg["MESSAGE"]}")
        elif msg.get("TYPE") == "REGISTERED":
            print(f"[Server]: {msg.get("MESSAGE")}")
        elif msg.get("TYPE") == "BROADCAST":
            print(f"[Broadcast] {msg.get("MESSAGE")}")
        else:
            print(f"Received unknown message type: {msg.get("TYPE")} - MSG: {msg.get("MESSAGE")}")


def main():
    # creates a socket and connects to the server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("72.62.81.113", 5000))

    user = input("Enter your username: ")
    send_message(s, {"TYPE": "SEND", "NAME": user})

    msg = recv_message(s)

    # print welcome message
    if msg and msg.get("TYPE") == "REGISTERED":
        print(f"\n[Server]: {msg.get("MESSAGE")}")

    # gets the chat rooms from the server from the regristration message
    chat_rooms = msg.get("CHAT_ROOMS") if msg else {}
    chat_room_name = None

    if len(chat_rooms) > 0:
        user_choice = None

        print("\nAvailable chat rooms:")

        for room, users in chat_rooms.items():
            print(f"- {room} (Owner: {users[0]})")
            print(f"  Users: {users}")

        print("\n")

        while user_choice != "y" and user_choice != "n":
            user_choice = input("Do you want to join an existing chat room? (y/n): ").lower()

        if user_choice == "y":

            while chat_room_name not in chat_rooms.keys():
                chat_room_name = input("Enter the name of the chat room to join: ")
            join_room(s, chat_room_name, chat_rooms)
            print("\n")

        else:
            chat_room_name = input("Enter a name for the new chat room: ")
            create_room(s, chat_room_name, chat_room_name)
            print("\n")
    else:
        print("No chat rooms available. Please create one on the server first.")
        chat_room_name = input("Enter a name for the new chat room: ")

        create_room(s, chat_room_name, chat_room_name)
        print("\n")

    msg = recv_message(s)
    if msg and msg.get("TYPE") == "JOINED":
        print(f"[Room]: {msg.get('MESSAGE')}\n")

    # Start the receiver thread
    t = threading.Thread(target=reciever_loop, args=(s,), daemon=True)
    t.start()

    # Sender loop
    while True:
        
        text = input()

        if not text:
            continue
        if text in ("exit", "quit"):
            break

        send_message(s, {"ROOM": chat_room_name, "TYPE": "SEND", "FROM": user, "MESSAGE": text})
    
    try:
        s.close()
    except:
        pass

if __name__ == "__main__":
    main()