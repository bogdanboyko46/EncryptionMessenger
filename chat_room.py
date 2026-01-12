# Relay server uses this class to send messages to everyone in chat room, 

from protocol import send_message

class chat_room:

    # new instance of chat_room object, creates a users list and automatically adds the user that created the obj to list
    def __init__(self, room_name, name, password=None):
        self.room_name = room_name
        self.admins = [name]
        self.members = [name]
        self.has_password = False
        self.ban_list = []

        if password:
            self.has_password = True
            self.password = password
        
        # The first person in list will be the owner of the room

    def get_chat_room_name(self):
        return self.room_name
    
    def add_user(self, name, socket=None, password=""):

        if self.has_password:
            if password == self.password:
                self.members.append(name)
            
            else:
                # only runs when a user is trying to join a password protected room with the wrong password, socket is provided when joining a password protected room
                send_message(socket, {"TYPE": "JOIN_REJECT", "MESSAGE": "The password entered was incorrect!"})
        else:
            self.members.append(name)
    
    # removes a user
    def remove_user(self, user):
        self.members.remove(user)

    # lists user
    def list_users(self):
        return self.members
    
    def get_owner(self):
        return self.admins[0]

    # broadcast msg to server, printing that a new user had joined the room, (displays for user that joined too)
    # passes to the send_message function below for slight optimization
    def broadcast(self, clients, name):
        self.handle_command("BROADCAST", f"Welcome to the chat room {name}!", clients)

    # Checks if a username is in a room (string -> boolean)
    def in_room(self, user):
        return user in self.members
    
    def handle_normal_message(self, msg, clients):
        
        # message is encrypted, message contents cannot be read besides metadata
        from_user = msg.get("FROM")

        for client in clients:
            if from_user == client:
                continue

            send_message(clients[client].get_socket(), msg)
    
    def handle_command(self, type, message, clients, from_user="", chat_rooms=None, pubkey_dir=None):

        # commands
        if type == "COMMAND":

            msglist = message.split(" ")
            command = msglist[0]

            # handles improper command formats, invalid users or self actions
            if len(msglist) == 2:
                if command not in ("!remove", "!makeadmin", "!ban"):
                    send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": "Invalid command format."})
                    return
                elif msglist[1] == from_user:
                    send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": "You cannot perform this action on yourself."})
                    return
                elif msglist[1] not in self.members:
                    send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": f"{msglist[1]} is not in the room."})
                    return
                
            # handles commands that should require additional arguments
            if len(msglist) == 1:
                if command in ("!remove", "!makeadmin", "!ban"):
                    send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": "Invalid command format."})
                    return
            
            # get the member count of the users and send rotate type msg to owner if member count changes
            mem_count = len(self.members)

            # admin commands
            if from_user in self.admins:
                
                print("INSIDE COMMAND ADMINS!!!!")
                user = msglist[1] if len(msglist) > 1 else None

                match command:
                    case "!remove":

                        # send message to client before removing from room to process the message
                        self.members.remove(user)
                        send_message(clients[user].get_socket(), {"TYPE": "REJOIN", "DISCONNECT_TYPE": "KICK", "MESSAGE": "You have been removed from the room by an admin."})

                        # message to the rest of the users that the user has been removed
                        self.handle_command("BROADCAST", f"{user} has been removed from the room by an admin.", clients)

                    case "!listusers":

                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": self.members})

                    case "!makeadmin":

                        # adds user to admin list and sends appropriate messages
                        self.admins.append(user)
                        new_admin_socket = clients[user].get_socket()
                        send_message(new_admin_socket, {"TYPE": "ADMIN"})
                        send_message(new_admin_socket, {"TYPE": "BROADCAST", "MESSAGE": "You have been made an admin by an existing admin."})
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": f"Made {user} admin"})

                    case "!ban":
                    
                        # send message to client before removing from room to process the message
                        self.ban_list.append(user)
                        self.members.remove(user)
                        send_message(clients[user].get_socket(), {"TYPE": "REJOIN", "DISCONNECT_TYPE": "BAN", "MESSAGE": "You have been banned from the room by an admin."})

                        # message to the rest of the users that the user has been banned
                        self.handle_command("BROADCAST", f"{user} has been banned from the room by an admin.", clients)

                    case "!banlist":
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": self.ban_list})

            # base commands

            print(f"ABOUT TO ENTER COMMAND WOARLDF FOR COMMAND ({command})")
            match command:
                # returns what type of role the user has (admin / guest)
        
                case "!role":
                    
                    if from_user in self.admins:
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": "You are an admin"})
                    else:
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": "You are a member"})

                case "!leave":
                        
                        was_owner = (from_user == self.get_owner())

                        if from_user in self.members:
                            self.members.remove(from_user)
                        if from_user in self.admins:
                            self.admins.remove(from_user)

                        if not self.members and chat_rooms:
                            del chat_rooms[self.room_name]

                        if not self.admins and self.members:
                            self.admins.append(self.members[0])
                            to_socket = clients[self.members[0]].get_socket()
                            send_message(to_socket, {"TYPE": "BROADCAST", "MESSAGE": "You have been made an admin by an existing admin."})
                            send_message(to_socket, {"TYPE": "ADMIN"})

                        if was_owner and self.admins:
                            new_owner = self.admins[0]
                            to_socket = clients[new_owner].get_socket()
                            send_message(to_socket, {"TYPE": "BROADCAST", "MESSAGE": "You have been made owner!"})
                            send_message(to_socket, {"TYPE": "OWNER"})
                        
                        self.handle_command("BROADCAST", f"{from_user} has left the room. Rotating keys.", clients)
                        # send rejoin message to the one who left
                        send_message(clients[from_user].get_socket(), {"TYPE": "REJOIN", "MESSAGE": "You have left the room."})
                case "!roomname":
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": f"The room name is: {self.room_name}"})
                case "!help":
                        help_msg = (
                            "Available commands:\n"
                            "!role - Check your role (admin/member)\n"
                            "!leave - Leave the chat room\n"
                            "!roomname - Get the name of the chat room\n"
                            "!help - Show this help message\n\n"
                        )

                        if from_user in self.admins:
                            help_msg += (
                                "Admin commands:\n"
                                "!remove <username> - Remove a user from the room\n"
                                "!listusers - List all users in the room\n"
                                "!makeadmin <username> - Make a user an admin\n"
                                "!ban <username> - Ban a user from the room\n"
                                "!banlist - Show the list of banned users\n"
                            )

                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": help_msg})
                case "!admins":
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": self.admins})
                
            if mem_count > len(self.members) and len(self.members) > 0 and chat_rooms:
                # member count has changed, send owner type rotate key message
                print("ROTATING NOW! SENDING TO ",self.get_owner())
                send_message(clients[self.get_owner()].get_socket(), {"TYPE": "ROTATE", "CHAT_ROOM": chat_rooms[self.room_name], "PUBKEY_DIR": pubkey_dir})

        else:
            for client in clients:
                if client == from_user:
                    continue

                send_message(clients[client].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": message})