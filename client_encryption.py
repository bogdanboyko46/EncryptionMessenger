import encryption_helper
import os

class ClientCrypto:
    def __init__(self):
        
        # create sign and dh keys
        self.sign_priv, self.sign_pub = encryption_helper.gen_sign_key_pair()
        self.dh_priv, self.dh_pub = encryption_helper.gen_dh_key_pair()
        
        self.peers = {}

class RoomCryptoState:
    def __init__(self, is_owner):

        self.room_key: bytes | None = None
        self.epoch: int | None = None

        self.is_owner = is_owner

        self.send_ctr: int
        self.recv_ctr: dict[str, int] = {}

        if self.is_owner:
            self.room_key = os.urandom(32)
            self.send_ctr = 0
            self.recv_ctr = {}

    def ins_as_creator(self):
        
        self.epoch = 1
        self.room_key = os.urandom(32)
        self.send_ctr = 0
        self.recv_ctr.clear()

    def ins_as_joiner(self):

        self.epoch = None
        self.room_key = None
        self.send_ctr = 0
        self.recv_ctr.clear

    def next_send_ctr(self):
        self.send_ctr += 1
        return self.send_ctr

    def is_replay(self, sender, ctr):
        last = self.recv_ctr[sender]
        return ctr <= last
    
    def mark_receieved(self, sender, ctr):
        self.recv_ctr[sender] = max(self.recv_ctr[sender], ctr)

    def rotate_key(self):
        
        if not self.is_owner:
            return
        
        self.room_key = os.urandom(32)
        self.send_ctr = 0
        self.recv_ctr.clear()





    