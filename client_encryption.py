<<<<<<< HEAD
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

    def set_room_key(self, rk):
        self.room_key = rk

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




    
=======
# all necessary imports
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def gen_sign_key_pair():
    sign_priv = ed25519.Ed25519PrivateKey.generate()
    return sign_priv, sign_priv.public_key()

def gen_dh_key_pair():
    ex_priv = x25519.X25519PrivateKey.generate()
    return ex_priv, ex_priv.public_key()

# sign payload (payload identity confirmation)
def sign(sign_priv, data):
    return sign_priv.sign(data)

# verify signed file
def verify(sign_pub, sig, data):
    sign_pub.verify(sig, data)

def hkdf(masked, context):
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=context
    )
    return hkdf.derive(masked)

def aead_encrypt(key32, msg, aad):
    nonce = os.urandom(12) # 96 bit nonce for GCM
    ct = AESGCM(key32).encrypt(nonce, msg, aad)
    return nonce, ct

def aead_decrypt(key32, nonce, encrypted_msg, aad):
    return AESGCM(key32).decrypt(nonce, encrypted_msg, aad)

>>>>>>> origin/main
