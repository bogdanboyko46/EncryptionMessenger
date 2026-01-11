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

    # get the private room key
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

    # get the NONCE and cipher text from the wrap key and context

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

    # verify sender sig
    owner_sign_pub.verify(msg["SIG"], aad(signed_part))

    eph_pub = bytes_to_dh_pub(msg["EPH_PUB"])
    shared = receiver_dh_priv.exchange(eph_pub)

    wrap_header = {
        "TYPE": "ROOM_KEY_WRAP",
        "TO": msg["TO"],
        "FROM": msg["FROM"],
        "EPH_PUB": msg["EPH_PUB"],
        "EPOCH": msg["EPOCH"],
    }
    # convert the context into bytes, then use the hkdf function to get the wrap key
    aad_bytes = aad(wrap_header)
    wrap_key = hkdf(shared, aad_bytes)

    # Decrypt room key using the wrap key and context
    room_key = aead_decrypt(
        wrap_key,
        msg["NONCE"],
        msg["CIPHERTEXT"],
        aad_bytes
    )

    return {"ROOM_KEY": room_key, "EPOCH": msg["EPOCH"]}

def encrypt_room_msg(sender_sign_priv, room_key, epoch, send_ctr, message, from_user, msg_type):

    info = {
        "FROM": from_user,
        "EPOCH": epoch,
    }

    info_bytes = aad(info)

    # wrapped room key using context info
    msg_key = hkdf(room_key, info_bytes)

    nonce = b"MSG0" + int(send_ctr).to_bytes(8, "big")

    # build aad
    aad_dict = {
        "TYPE": msg_type,
        "EPOCH": epoch,
        "CTR": send_ctr,
        "FROM": from_user,
    }

    aad_bytes = aad(aad_dict)

    # payload to encrypt
    payload = json.dumps(
        {"MESSAGE": message},
        separators=(",", ":"), sort_keys=True).encode("utf-8")
    
    # encrypt
    ct = AESGCM(msg_key).encrypt(nonce, payload, aad_bytes)

    wrap_msg = {
        "TYPE": msg_type,
        "EPOCH": epoch,
        "CTR": send_ctr,
        "FROM": from_user,
        "NONCE": nonce,
        "CIPHERTEXT": ct,
    }

    sign_bytes = sign(sender_sign_priv, aad(wrap_msg))
    wrap_msg["SIG"] = sign_bytes

    return wrap_msg


def decrypt_room_message(receiver_sign_pub, room_key, msg, recv_ctr):
    sender = msg["FROM"]
    epoch = msg["EPOCH"]
    ctr = msg["CTR"]

    last = recv_ctr.get(sender, -1)
    if ctr <= last:
        raise ValueError(f"Out of order ctr - from {sender}: ctr={ctr} last={last}")

    # verify the material
    signed_part = {
        "TYPE": msg["TYPE"],
        "EPOCH": epoch,
        "CTR": ctr,
        "FROM": sender,
        "NONCE": msg["NONCE"],
        "CIPHERTEXT": msg["CIPHERTEXT"],
    }

    # verify that material comes from the actual sender!
    receiver_sign_pub.verify(msg["SIG"], aad(signed_part))

    # derive sender key - exact contents and format
    info_bytes = aad({
        "FROM": sender,
        "EPOCH": epoch,
    })

    msg_key = hkdf(room_key, info_bytes)

    # 3) recompute AAD exactly
    aad_dict = {
        "TYPE": msg["TYPE"],
        "EPOCH": epoch,
        "CTR": ctr,
        "FROM": sender,
    }

    aad_bytes = aad(aad_dict)

    # decrypt
    pt = AESGCM(msg_key).decrypt(msg["NONCE"], msg["CIPHERTEXT"], aad_bytes)

    # parse payload
    payload = json.loads(pt.decode("utf-8"))
    recv_ctr[sender] = ctr
    return payload["MESSAGE"]

def rotate_room_key(owner_name, sign_priv, pubkey_dir, chat_room, epoch):
    new_room_key = os.urandom(32)

    # update epoch
    epoch += 1

    wraps = []

    # msg, owner_sign_priv, room_key, from_name, epoch

    for mem in chat_room.members:
        
        if mem is chat_room.get_owner():
            continue

        user_info = {
            "DH_PUB": pubkey_dir[mem]["dh_pub"],
            "NAME": mem,
        }

        wrap = owner_handle_key_wrap(
            user_info,
            sign_priv,
            new_room_key,
            owner_name,
            epoch
        )

        wraps.append(wrap)
    
    return new_room_key, wraps