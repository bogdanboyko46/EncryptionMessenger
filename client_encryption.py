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

