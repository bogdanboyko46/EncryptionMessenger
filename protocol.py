import json, struct

def send_message(sock, obj: dict):
    # converts dict into JSON string then encodes to bytes
    data = json.dumps(obj).encode("utf-8")
    # creates a 4 byte header with length of data and sends it with the data
    sock.sendall(struct.pack("!I", len(data)) + data)

# Helper function to receive an exact number of bytes
def recv_exact(sock, n: int) -> bytes:
    # stores received byte chunks
    chunks = []
    got = 0
    # keeps receiving until n bytes are received
    while got < n:
        chunk = sock.recv(n - got)
        if not chunk:
            return b""
        chunks.append(chunk)
        got += len(chunk)
    return b"".join(chunks)

# Receives a message and returns the decoded dict
def recv_message(sock):
    # reads the 4 byte header first
    header = recv_exact(sock, 4)

    if not header:
        return None
    
    # converts 4 byte back into an int, then stores in tuple
    # that is why the comma is there
    (length,) = struct.unpack("!I", header)

    # now reads the actual data based on length from header
    body = recv_exact(sock, length)
    if not body:
        return None
    
    # decodes bytes back into dict and returns it
    return json.loads(body.decode("utf-8"))
