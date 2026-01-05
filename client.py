# Important to note, for vast majority of code "messages" arent actually referring to actual typed messages
# It refers to the bytes sent between clients & relay_server, these messages for most part contain 
# socket & a map of instructions

import time
import socket
import threading
import queue
from protocol import recv_message, send_message

state = {
    "RUNNING": True,
    "IN_ROOM": False,
    "ROOM": None,
    "USER": None,
}

inbox = queue.Queue()   # messages from server (dicts)
outbox = queue.Queue()  # messages to be sent to relay server (dicts)

prompts_box = queue.Queue() # prompts that the user answers to (dicts -> PROMPT, RESPONSE BOUNDARIES ie ("y" or "n"))
user_input_box = queue.Queue() # input messages from client (strings)

# user choice to either create a new room or join one currently if there are any available
def room_assignment_action(chat_rooms):
    # display all chat rooms to user via console

    print()
    if chat_rooms:
        
        print("Current Chat Rooms: ")
        for chat_room_name, chat_room_obj in chat_rooms.items():
            print(f"{chat_room_name} - Owner: {chat_room_obj.get_owner()} - Users: {chat_room_obj.list_users()}")
        print()

        # .get() function waits for the user to input a choice
        prompts_box.put({"PROMPT": "Would you like to join a room on the server? (y/n): ", "BOUNDARIES": ("y", "n")})
        print()
        
        return user_input_box.get() == "n"
    else:

        print("There are currently no chat rooms on the server. ", end="")

    # returning none denotes that the user intends / needs to make a new room
    return True

def room_assignment(chat_rooms):

    # a password that a user decides to create when making a new room / when joining a password-protected room
    password = None

    # the name of the chat room to create / join
    room_name = None

    # user intends / needs to make a new room
    if room_assignment_action(chat_rooms):
 
        # gathers the user's new room name
        prompts_box.put({"PROMPT": "Please enter the room of the new chat room: "})
        room_name = user_input_box.get()

        print()

        # asks the user if they'd like to create a password
        prompts_box.put({"PROMPT": "Would you like to create a password for your room? (y/n): ", "BOUNDARIES": ("y", "n")})

        if user_input_box.get() == "y":

            # the user intends to create a password, store a non-null, non-empty value inside of password
            prompts_box.put({"PROMPT": "Please create a password for the room: "})
            password = user_input_box.get()
            print()
        
        # finally add to outbox - will be sent to relay server
        outbox.put({"TYPE": "CREATE_ROOM", "ROOM_NAME": room_name, "PASSWORD": password})

    else:

        # user will now choose what room they want to join
        prompts_box.put({"PROMPT": "Please enter the room you'd like to join: ", "BOUNDARIES": tuple(chat_rooms.keys())})
        room_name = user_input_box.get()
        print()

        # checks to see whether there is a password for the room
        if chat_rooms[room_name].has_password:
            # password logic
            prompts_box.put({"PROMPT": "Please enter the password for the room: "})
            password = user_input_box.get()
            print()

        # finally add to outbox - will be sent to relay server
        outbox.put({"TYPE": "JOIN_ROOM", "ROOM_NAME": room_name, "PASSWORD": password})

# ALL THREAD FUNCTIONS 
def recieving_thread(s):
    while state["RUNNING"]:

        msg = recv_message(s)
        # in the case of a null msg sent to socket
        
        if msg is None:
            print("Disconnected from server.")
            state["RUNNING"] = False
            s.close()
            break
        
        inbox.put(msg)

def outbox_thread(s):
    while state["RUNNING"]:

        # waits for contents patiently
        contents = outbox.get()

        # invalid contents if condition passes; either null or contains nothing
        if contents is None or not contents:
            continue

        # else, we send the contents to the relay server
        send_message(s, contents)

# helper function to not repeat duplicate computations in user_input_thread()
def input_helper(prompt_dict={}):

    user_inp = None

    prompt = ""
    boundaries = tuple()

    # in the case of a prompt that the user needs to answer
    if prompt_dict:

        prompt = prompt_dict.get("PROMPT")
        
        if prompt_dict.get("BOUNDARIES"):
            boundaries = prompt_dict.get("BOUNDARIES")

        # else, we know that it is a user trying to send a message to the room
    
    while (
        user_inp is None or
        boundaries and user_inp not in boundaries
    ):
        user_inp = input(prompt).strip()

    # run code in while loop if user_inp is null, empty, or is NOT in a tuple of accepted inputs IF boundaries WITH contents is passed
    return user_inp

def user_input_thread():
    while state["RUNNING"]:
        
        # constantly runs - nothing stops this thread! user input is always being attempted
        # prompts queue has priority over message input to room

        if not prompts_box.empty():
            
            prompt = prompts_box.get()
            user_response = ""

            while not user_response:
                user_response = input_helper(prompt)

            user_input_box.put(user_response)

        # if the queue has contents inside - the user is being prompted
        elif state["IN_ROOM"]:
            
            # get user inp
            user_response = input_helper()

            # append user message to outbox, for it to be sent to relay server
            if user_response:
                outbox.put({"TYPE": "SEND", "MESSAGE": user_response})

        time.sleep(.15)

def main():
    # Create a TCP/IP socket, connect to the VPS IP address & port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("72.62.81.113", 5000))

    # create threads
    rec_thread = threading.Thread(target = recieving_thread, args=(s,))
    input_thread = threading.Thread(target = user_input_thread, args=())
    outbx_thread = threading.Thread(target = outbox_thread, args=(s,))

    input_thread.start()
    rec_thread.start()
    outbx_thread.start()

    # set the username of the client
    prompts_box.put({"PROMPT": "Please enter your username: "})
    state["USER"] = user_input_box.get()

    # send initial registration message to server
    outbox.put({"NAME": state["USER"]})
    
    # waits to recieve the message from the relay server
    server_info = inbox.get()
    
    # prints 'Welcome to the VPS Server, {name}!'
    print(f"[SERVER]: {server_info.get("MESSAGE")}")
    
    # initial room assignment
    room_assignment(server_info.get("CHAT_ROOMS"))

    while state["RUNNING"]:
        
        # inbound logic - checks to see if inbox queue is empty
        msg = inbox.get()

            # gets the type of the message
        mType = msg.get("TYPE")

        match mType:
            
            # message type that indicates a logic error
            case "ERROR":
                    
                error_message = msg.get("MESSAGE")

                print(f"[Error]: {error_message}")
                state["RUNNING"] = False

            # message type that disconnected a user from a room, user now needs room reassignment
            case "REJOIN":
                
                 # drain anything from current inbox
                try:
                    inbox.get_nowait()
                except queue.Empty:
                    pass

                print(f"\n[Server]: {msg.get("MESSAGE")}\n")

                # unassign user flags
                state["IN_ROOM"] = False
                state["ROOM"] = None
                
                if msg.get("DISCONNECT_TYPE") and msg.get("DISCONNECT_TYPE") in ("REMOVE", "BAN"):
                    print("Please hit enter to continue.\n")

                room_assignment(msg.get("CHAT_ROOMS"))

            case "CONNECTED":
                    
                # confirms and flags the user in a room and assigns the corresponding room name
                room_name = msg.get("ROOM_NAME")
                state["IN_ROOM"] = True
                state["ROOM"] = room_name

            # inbound messages coming from other users in the assigned room
            case "RECEIVE":

                from_user = msg.get("FROM")
                user_message = msg.get("MESSAGE")

                print(f"{from_user}: {user_message}")

            # broadcast messages that share important, or relevant information from the chat room
            case "BROADCAST":
                    
                broadcast_message = msg.get("MESSAGE")

                print(f"[BROADCAST]: {broadcast_message}\n")
                    
            # message type that confirms connection to a room
            

if __name__ == "__main__":
    main()