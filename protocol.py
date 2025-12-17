# protocol.py
import struct

# Parameters are socket (tcp socket), name (clientA / oisin's pc), the message being sent("hello world")
def send_message(sock, name: str, message: str):
    # encodes name to byte object
    name_bytes = name.encode("utf-8")
    # encodes message to byte object
    msg_bytes = message.encode("utf-8")


    # struct.pack converts numbers into readable bytes, the "!H" represents it will be 2 bytes long
    payload = (
        struct.pack("!H", len(name_bytes)) +
        name_bytes +
        # "!I" represents it will be 4 bytes long
        struct.pack("!I", len(msg_bytes)) +
        msg_bytes
    )
    # Sends out message from the socket
    sock.sendall(payload)


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Disconnected")
        data += chunk
    return data


def recv_message(sock):
    name_len = struct.unpack("!H", recv_exact(sock, 2))[0]
    name = recv_exact(sock, name_len).decode("utf-8")

    msg_len = struct.unpack("!I", recv_exact(sock, 4))[0]
    msg = recv_exact(sock, msg_len).decode("utf-8")

    return name, msg
