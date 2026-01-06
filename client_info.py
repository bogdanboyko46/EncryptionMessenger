class Client:
    
    def __init__(self, socket, user_name):
        self.socket = socket
        self.user_name = user_name

    def get_name(self):
        return self.user_name
    
    def get_socket(self):
        return self.socket
    