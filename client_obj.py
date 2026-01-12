class Client:
    
    def __init__(self, socket, user_name):
        self.socket = socket
        self.user_name = user_name
        self.room_history = []
        self.pinned_keys = dict() # stores receiving user name -> "sign_pub": {sign_pub}, "ex_pub" = {ex_pub}

    def get_name(self):
        return self.user_name
    
    def get_socket(self):
        return self.socket
    
    def add_room_history(self, room_name):
        self.room_history.append(room_name)

    def delete_room_history(self, room_name):
        self.room_history.remove(room_name)
    