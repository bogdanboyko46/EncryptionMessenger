from protocol import send_message

class chat_room:

    users = []

    def __init__(self, room_name, socket, name):
        self.room_name = room_name
        self.add_user(name)

    def add_user(self, name):
        self.users.append(name)
    
    def remove_user(self, user):
        self.users.remove(user)

    def list_users(self):
        return self.users

    # def broadcast(self, socket, name):
    #    send_message(socket, {"NAME": name, "ROOM": self.room_name, "TYPE": "BROADCAST", "MESSAGE": f"Welcome to the chat room {name}!"})

    def in_room(self, user):
        return user in self.users
    
    def send_message(self, from_user, message, sockets_dict):
        for user in self.users:
            if user != from_user:
                send_message(sockets_dict[user], {"TYPE": "RECIEVE", "FROM": from_user, "MESSAGE": message})