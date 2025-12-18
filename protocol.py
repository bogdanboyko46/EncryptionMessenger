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
    # Create an empty bytes object.
    # This will accumulate data until we have exactly n bytes.
    data = b""

    # Keep looping until we have read n bytes in total
    while len(data) < n:

        # Ask the OS for the remaining number of bytes.
        # IMPORTANT:
        # - recv() may return fewer bytes than requested
        # - recv() BLOCKS here until at least 1 byte arrives
        chunk = sock.recv(n - len(data))

        # If recv() returns b"":
        # - the peer closed the connection
        # - continuing would corrupt the protocol
        if not chunk:
            raise ConnectionError("Disconnected")

        # Append the newly received bytes
        # This is what "moves forward" in the TCP stream
        data += chunk

    # At this point, data is EXACTLY n bytes long
    return data

# In over-simplified terms, the message recieved will be an array of bytes
# The message will have 2 "parts"
# Authors name, and the content of message
# If the message was "Oisin: Hello everyone"
# It would be "5, Oisin, 14, Hello everyone"
# 5 is length of message author "oisin"
# 14 is length of message "Hello eveyone"
def recv_message(sock):

    # This will find the length of the bytes for message
    name_len_bytes = recv_exact(sock, 2)

    
    name_len = struct.unpack("!H", name_len_bytes)[0]

    # ---- STEP 2: READ NAME ----
    # Now that we know the name length,
    # read exactly that many bytes.
    name_bytes = recv_exact(sock, name_len)

    # Convert bytes → string
    name = name_bytes.decode("utf-8")

    # ---- STEP 3: READ MESSAGE LENGTH ----
    # Read exactly 4 bytes for the message length.
    msg_len_bytes = recv_exact(sock, 4)

    # Convert those 4 bytes into a Python integer.
    msg_len = struct.unpack("!I", msg_len_bytes)[0]

    # ---- STEP 4: READ MESSAGE ----
    # Read exactly msg_len bytes from the stream.
    msg_bytes = recv_exact(sock, msg_len)

    # Convert bytes → string
    msg = msg_bytes.decode("utf-8")

    # Return one COMPLETE logical message
    return name, msg

