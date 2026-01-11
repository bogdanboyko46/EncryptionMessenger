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
pubkey_dir = dict() # username -> record
lock = threading.Lock()

def create_room(room_name, owner, password=None):
    # create a new chat_room obj and assign respective room name to room object

    # check to see if the room already exists
    if room_name in chat_rooms:
        send_message(clients[owner].get_socket(), {"TYPE": "CREATE_REJECT", "MESSAGE": "Room already exists!"})
        return False

    temp_room = chat_room(room_name, owner, password)
    chat_rooms[room_name] = temp_room

    return True
    # Prints out the room name and its creator

# the computation for assigning a user to a room, prompts user to join or create one
def assign_room(conn, name, msg):
    room_name = msg["ROOM_NAME"] if msg else None

    # handles whether the client wants to join or create a room

    if not msg:
        return
    
    mtype = msg.get("TYPE")

    if mtype == "CREATE_ROOM":
        
        # if a room was not able to be created, we return and do not create new room
        if not create_room(room_name, name, msg.get("PASSWORD")):
            return

    elif mtype == "JOIN_ROOM":
        # if user intends to join a room, it utilizes the add_user() function and adds the respective user
        
        # handles if the user is banned from the room or if the room does not exist
        if room_name not in chat_rooms.keys() or name in chat_rooms[room_name].ban_list:
            send_message(conn, {"TYPE": "JOIN_REJECT", "CHAT_ROOMS": chat_rooms, "MESSAGE": "Room does not exist or you are banned from it!"})
            return None
        
        room = chat_rooms.get(room_name)
        if room:
            if room.has_password:
                room.add_user(name, conn, msg.get("PASSWORD"))

                # if user ended up not being in the room because of an incorrect password, we can apply a simple check to break out of the function
                if not name in room.members:
                    return None
                
            else:
                room.add_user(name)
        else:
            return None
        
        # rotate key process -> send to owner, gen new room key and distribute to everyone   

    send_message(conn, {"TYPE": "CONNECTED", "CHAT_ROOM": chat_rooms[room_name]})

    # send rotate msg to owner
    if mtype == "JOIN_ROOM":
        send_message(clients[chat_rooms[room_name].get_owner()].get_socket(), {
            "TYPE": "ROTATE", 
            "PUBKEY_DIR": pubkey_dir, 
            "CHAT_ROOM": chat_rooms[room_name]
            })

    # add room to room history
    if room_name not in clients[name].room_history:
        clients[name].add_room_history(room_name)
    
    return room_name

def establish_connection(conn):
    msg = recv_message(conn)

    if not msg:
        send_message(conn, {"TYPE": "ERROR", "MESSAGE": "Invalid registration message"})
        conn.close()
        return None
    
    if msg.get("TYPE") != "PUBKEYS":
        send_message(conn, {"TYPE":"ERROR","MESSAGE":"Expected PUBKEYS registration"})
        conn.close()
        return None

    name = msg.get("NAME")
    if not name:
        send_message(conn, {"TYPE": "ERROR", "MESSAGE": "Invalid registration message"})
        conn.close()
        return None
    

    if name in clients:
        send_message(conn, {"TYPE": "ERROR", "MESSAGE": "Name already taken"})
        conn.close()
        return None

    sign_pub = msg.get("SIGN_PUB")
    dh_pub = msg.get("DH_PUB")

    pubkey_dir[name] = {"sign_pub": sign_pub, "dh_pub": dh_pub}

    send_message(conn, {
        "TYPE": "REGISTRATION",
        "CHAT_ROOMS": chat_rooms,
        "MESSAGE": f"Welcome to the chat room server, {name}!"
    })

    clients[name] = Client(conn, name)
    return name

# Every client thats connected to the relay server will have an instance of this (the instance is hosted here ofc)
def handle_client(conn, addr):
    print(f"[+] Connected: {addr}")

    name = establish_connection(conn)
    if name is None:
        return

    chat_room_name = None

    try:
        while True:
            msg = recv_message(conn)
            if msg is None:
                break

            mType = msg.get("TYPE")

            if mType in ("CREATE_ROOM", "JOIN_ROOM"):
                chat_room_name = assign_room(conn, name, msg)

            match mType:
                case "SEND":
                    # message is encrypted, route the message to the users in the chat room
                    print("CIPHER TEXT: ",msg["CIPHERTEXT"])
                    chat_rooms[chat_room_name].handle_normal_message(msg, clients)
                
                case "COMMAND":
                    
                    # commands are NOT encrypted
                    chat_rooms[chat_room_name].handle_command(
                        mType, 
                        msg.get("MESSAGE"), 
                        clients, from_user=name, 
                        chat_rooms=chat_rooms, 
                        pubkey_dir=pubkey_dir
                        )

                case "RELOAD":
                    # send the client the current chat rooms
                    send_message(conn, {"TYPE": "RELOAD", "CHAT_ROOMS": chat_rooms})

                case "ROOM_KEY_WRAP":
                    # reroute to the respective user

                    print("GOT!!")
                    
                    TO = msg.get("TO")

                    if TO in clients:

                        msg["PUBKEY_DIR"] = pubkey_dir
                        send_message(clients[msg.get("TO")].get_socket(), msg)

                case "DISCONNECT":
                    break

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        print(f"[-] User disconnected: {name} from {addr}")
        # cleanup on disconnect
        with lock:
            
            # delete name from pubkey directory
            if name in pubkey_dir:
                del pubkey_dir[name]

            # get user room history
            # user_room_history = clients[name].room_history or {}

            if name in clients:
                del clients[name]

            # if the user was in a room, remove them from it
            if chat_room_name and chat_room_name in chat_rooms:
                room = chat_rooms[chat_room_name]
                if name in room.members:
                    room.remove_user(name)
                    room.handle_command("BROADCAST", f"{name} has left the room.", clients, from_user=name)

                # deleted rooms are wiped from a clients history
                # for room in user_room_history:
                    # if name in chat_rooms[room].ban_list:
                        # chat_rooms[room].ban_list.remove(name)

                if len(chat_rooms[chat_room_name].members) == 0:
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

    