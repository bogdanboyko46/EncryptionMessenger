import socket

# we need threading to stop multiple clients using same function anyway
import threading
from chat_room import chat_room
from protocol import send_message, recv_message
from client_info import Client

HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 5000        # Port clients will connect to

clients = dict()     # dict, maps user name -> client obj
chat_rooms = dict()  # Dictionary to hold chat room instances, maps room name -> Room instance
lock = threading.Lock()

def create_room(room_name, owner, password=None):
    # create a new chat_room obj and assign respective room name to room object

    # check to see if the room already exists
    if room_name in chat_rooms:
        send_message(clients[owner].get_socket(), {"TYPE": "REJOIN", "MESSAGE": "Room already exists!"})
        return
    
    temp_room = chat_room(room_name, owner, password)
    chat_rooms[room_name] = temp_room
    # Prints out the room name and its creator

# the computation for assigning a user to a room, prompts user to join or create one
def assign_room(conn, name, msg):
    room_name = msg["ROOM_NAME"] if msg else None

    # handles whether the client wants to join or create a room
    if msg and msg.get("TYPE") == "CREATE_ROOM":

        create_room(room_name, name, msg.get("PASSWORD"))
        
    elif msg and msg.get("TYPE") == "JOIN_ROOM":
        # if user intends to join a room, it utilizes the add_user() function and adds the respective user
        
        # handles if the user is banned from the room or if the room does not exist
        if name in chat_rooms[room_name].ban_list:
            send_message(conn, {"TYPE": "REJOIN", "CHAT_ROOMS": chat_rooms, "MESSAGE": "Room does not exist or you are banned from it!"})
            return None
        
        room = chat_rooms.get(room_name)
        if room:
            if room.has_password:
                room.add_user(name, conn, msg.get("PASSWORD"))
            else:
                room.add_user(name)
        else:
            return None

    print(f"[DEBUG] {name} has joined room: {room_name}")
    chat_rooms[room_name].broadcast(clients, name)

    print(f"IS {room_name} in chat rooms: {room_name in chat_rooms}")
    send_message(conn, {"TYPE": "CONNECTED", "ROOM_NAME": room_name})

    return room_name

# Every client thats connected to the relay server will have an instance of this (the instance is hosted here ofc)
def handle_client(conn, addr):
    # prints the ip address of the client that connects to the relay
    print(f"[+] Connected: {addr}")

    msg = recv_message(conn)
    name = None

    # recieves the name from the client
    if msg:
        name = msg.get("NAME")

    # if the name is empty, then it closes the TCP socket of that client and returns
    if not name:
        send_message(conn, {"TYPE": "ERROR", "MESSAGE": "Invalid registration message"})
        conn.close()
        return
        
    # checks if the name is already taken, gives an "ERROR" type message
    if name in clients:
        send_message(conn, {"TYPE": "ERROR", "MESSAGE": "Name already taken"})
        conn.close()
        return

    # send message with chat_room info
    send_message(conn, {"TYPE": "REGISTRATION", "CHAT_ROOMS": chat_rooms, "MESSAGE": f"Welcome to the chat room server, {name}!"})

    # receives msg for room assignment
    client_registration = recv_message(conn)

    # assigns the client as a key - value pair in the clients dict
    clients[name] = Client(conn, name, client_registration)
    chat_room_name = assign_room(conn, name, client_registration)

    # maps client name -> client object

    # broadcasts user to room regardless if they created it or joined
    try:
        while True:
           
            # waits for message in the main loop
            msg = recv_message(conn)

            if msg is None:
                break
            
            mType = msg.get("TYPE")

            if mType in ("CREATE_ROOM", "JOIN_ROOM"):
                chat_room_name = assign_room(conn, name, msg)
                continue

            match mType:
                case "SEND":
                    # operation for a user sending a message to the room they are in
                    message = msg.get("MESSAGE")

                    print(f"THE MESSAGE IS {message}")

                    if chat_room_name in chat_rooms:
                        print("SENDING NOW!")
                        chat_rooms[chat_room_name].send_message("RECEIVE", message, clients, from_user=name, chat_rooms=chat_rooms)

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        print(f"[-] User disconnected: {name} from {addr}")
        # cleanup on disconnect
        with lock:
            if name in clients:
                del clients[name]
            # if the user was in a room, remove them from it
            if chat_room_name and chat_room_name in chat_rooms:
                room = chat_rooms[chat_room_name]
                if name in room.users:
                    room.remove_user(name)
                    room.send_message("BROADCAST", f"{name} has left the room.", clients, from_user=name)
                
                if len(chat_rooms[chat_room_name].users) == 0:
                    del chat_rooms[chat_room_name]
                    print(f"[+] Room '{chat_room_name}' deleted due to no users remaining.")
            # send a message to the rest of the users that the user has left
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

    