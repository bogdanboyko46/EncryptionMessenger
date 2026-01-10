from cryptography.hazmat.primitives.asymmetric import ed25519, x25519

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import json
import base64

from cryptography.hazmat.primitives import serialization

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


# convert metadata dict to bytes, 
def aad(d: dict) -> bytes:
    def conv(x):
        if isinstance(x, (bytes, bytearray)):
            return base64.b64encode(bytes(x)).decode("ascii")
        return x

    return json.dumps(
        {k: conv(v) for k, v in d.items()},
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

# get the eph session key for the receiver end
def eph_session_key(eph_priv, joiner_eph_pub):
    return eph_priv.exchange(joiner_eph_pub)

# convert dh public key in form of bytes to obj
def bytes_to_obj(eph_dh_bytes):
    return x25519.X25519PublicKey.from_public_bytes(eph_dh_bytes)

# recieve the session key during key exchange, get the session key
def get_session_key(dh_priv, eph_pub):
    return dh_priv.exchange(eph_pub)

def bytes_to_sign_pub(sign_pub_bytes: bytes):
    return ed25519.Ed25519PublicKey.from_public_bytes(sign_pub_bytes)

def bytes_to_dh_pub(dh_pub_bytes: bytes):
    return x25519.X25519PublicKey.from_public_bytes(dh_pub_bytes)

def sign_pub_bytes(sign_pub):
    return sign_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

def dh_pub_bytes(dh_pub):
    return dh_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

def owner_handle_key_wrap(msg, owner_sign_priv, room_key, from_name, epoch):
    # get the public user's dh pub key
    joiner_dh_pub = bytes_to_obj(msg.get("DH_PUB"))

    eph_dh_priv, eph_dh_pub = gen_dh_key_pair()

    payload = room_key

    aad_dict = {
        "TYPE": "ROOM_KEY_WRAP",
        "TO": msg.get("NAME"),
        "FROM": from_name,
        "EPH_PUB": dh_pub_bytes(eph_dh_pub),
        "EPOCH": epoch,
        }

        # convert context into bytes and obtain the session key
    aad_bytes = aad(aad_dict)
    secret_key = eph_session_key(eph_dh_priv, joiner_dh_pub)
            
        # get the wrapped key
    wrap_key = hkdf(secret_key, aad_bytes)

    NONCE, CIPHERTEXT = aead_encrypt(
        wrap_key,
        payload,
        aad_bytes
    )

    wrap_msg = dict(aad_dict)
    wrap_msg["NONCE"] = NONCE
    wrap_msg["CIPHERTEXT"] = CIPHERTEXT

    sign_bytes = sign(owner_sign_priv, aad(wrap_msg))
    wrap_msg["SIG"] = sign_bytes
    
    return wrap_msg

def receiver_handle_key_wrap(msg, receiver_dh_priv):
    pubkey_dir = msg.get("PUBKEY_DIR") or {}
    owner = msg.get("FROM")
    if not owner or owner not in pubkey_dir:
        raise ValueError("Missing owner pubkey entry")

    owner_sign_pub_bytes = pubkey_dir[owner]["sign_pub"]
    owner_sign_pub = bytes_to_sign_pub(owner_sign_pub_bytes)

    # Verify signature over exactly what sender signed
    signed_part = {
        "TYPE": msg["TYPE"],
        "TO": msg["TO"],
        "FROM": msg["FROM"],
        "EPH_PUB": msg["EPH_PUB"],
        "EPOCH": msg["EPOCH"],
        "NONCE": msg["NONCE"],
        "CIPHERTEXT": msg["CIPHERTEXT"],
    }
    owner_sign_pub.verify(msg["SIG"], aad(signed_part))

    # Derive wrap key
    eph_pub = bytes_to_dh_pub(msg["EPH_PUB"])
    shared = receiver_dh_priv.exchange(eph_pub)

    wrap_header = {
        "TYPE": "ROOM_KEY_WRAP",
        "TO": msg["TO"],
        "FROM": msg["FROM"],
        "EPH_PUB": msg["EPH_PUB"],
        "EPOCH": msg["EPOCH"],
    }
    aad_bytes = aad(wrap_header)
    wrap_key = hkdf(shared, aad_bytes)

    # Decrypt room key
    room_key = aead_decrypt(
        wrap_key,
        msg["NONCE"],
        msg["CIPHERTEXT"],
        aad_bytes
    )

    return {"ROOM_KEY": room_key, "EPOCH": msg["EPOCH"]}

