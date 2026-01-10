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
        self.send_message("BROADCAST", f"Welcome to the chat room {name}!", clients)

    # Checks if a username is in a room (string -> boolean)
    def in_room(self, user):
        return user in self.members
    
    # from_user is a default argument so broadcast msg essentially "bypasses" the check within the loop, printing to the user that joined also
    def send_message(self, type, message, clients, from_user="", chat_rooms=None):

        # edge case where user was able to send a message to the room but not is allowed anymore (kicked or banned)
        
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
                    
            # admin commands
            if from_user in self.admins:
                
                user = msglist[1] if len(msglist) > 1 else None

                match command:
                    case "!remove":

                        # send message to client before removing from room to process the message
                        self.members.remove(user)
                        send_message(clients[user].get_socket(), {"TYPE": "REJOIN", "DISCONNECT_TYPE": "KICK", "MESSAGE": "You have been removed from the room by an admin."})

                        # message to the rest of the users that the user has been removed
                        self.send_message("BROADCAST", f"{user} has been removed from the room by an admin.", clients)

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
                        self.send_message("BROADCAST", f"{user} has been banned from the room by an admin.", clients)

                    case "!banlist":
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": self.ban_list})

            # base commands
            match command:
                # returns what type of role the user has (admin / guest)
                
                case "!role":
                    
                    if from_user in self.admins:
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": "You are an admin"})
                    else:
                        send_message(clients[from_user].get_socket(), {"TYPE": "BROADCAST", "MESSAGE": "You are a member"})

                case "!leave":
                        
                        self.members.remove(from_user)

                        if from_user in self.admins:
                            self.admins.remove(from_user)

                            # the first user in the list becomes admin if admin leaves
                            if len(self.admins) == 0 and len(self.members) > 0:
                                self.admins.append(self.members[0])

                                # send admin msg to user - update's user scene
                                to_socket = clients[self.admins[0]].get_socket()
                                send_message(to_socket, {"TYPE": "BROADCAST", "MESSAGE": "You have been made an admin by an existing admin."})
                                send_message(to_socket, {"TYPE": "ADMIN"})

                        if len(self.members) == 0:
                            # the only user will be an admin, so delete room

                            # loop thru clients and remove the room in their history
                            for client in clients.values():
                                if self.room_name in client.room_history:
                                
                                    client.delete_room_history(self.room_name)
                                    
                            if chat_rooms:
                                # delete room from server and unassign user from room
                                del chat_rooms[self.room_name]

                                # check if the chat room is empty and room from chat rooms if so
                        
                        if len(self.members) > 0:

                            print("BROADCASTING!!!!!!")
                            self.send_message("BROADCAST", f"{from_user} has left the room.", clients)

                        send_message(clients[from_user].get_socket(), {"TYPE": "REJOIN", "MESSAGE": "You have left the room."})
                        # message to the rest of the users that the user has left
                        
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
                        
             
        else:
            # loops thru every user in that room and sends the corresponding message to them
            # .get_socket() is function in client.
            print("SENDING MESSAGE TO OTHER USERS!")
            for user in self.members:
                print(f"ABOUT TO SEND MESSAGE TO {user}!")
                if user != from_user:
                    send_message(clients[user].get_socket(), {"TYPE": type, "FROM": from_user, "MESSAGE": message})