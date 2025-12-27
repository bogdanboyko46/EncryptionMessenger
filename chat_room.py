from protocol import send_message

class chat_room:

    # new instance of chat_room object, creates a users list and automatically adds the user that created the obj to list
    def __init__(self, room_name, name):
        self.room_name = room_name
        self.users = []
        self.add_user(name)

    def add_user(self, name):
        self.users.append(name)
    
    def remove_user(self, user):
        self.users.remove(user)

    def list_users(self):
        return self.users

    # broadcast msg to server, printing that a new user had joined the room, (displays for user that joined too)
    # passes to the send_message function below for slight optimization
    def broadcast(self, sockets_dict, name):
        self.send_message("BROADCAST", f"Welcome to the chat room {name}!", sockets_dict)

    def in_room(self, user):
        return user in self.users
    
    # from_user is a default argument so broadcast msg essentially "bypasses" the check within the loop, printing to the user that joined also
    def send_message(self, type, message, sockets_dict, from_user=""):
        # loops thru every user in that room and sends the corresponding message to them
        for user in self.users:
            if user != from_user:
                print(f"SENT TO USER {user}! MSG: {message}")
                send_message(sockets_dict[user], {"TYPE": type, "FROM": from_user, "MESSAGE": message})