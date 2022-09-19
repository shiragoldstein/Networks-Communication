import socket
import sys

# save the arguments
IP = sys.argv[1]
PORT = int(sys.argv[2])
FILE = sys.argv[3]

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(5)
f = open(FILE, "rb")
int_index = 1
byte_index = int_index.to_bytes(4, "little")
byte = f.read(96)

while byte:
    while True:
        if byte == bytes(0):
            break
        s.sendto(byte_index + byte, (IP, PORT))
        try:
            data, addr = s.recvfrom(1024)
            # print(str(data[4:100]), addr)
            byte = f.read(96)
            int_index = int_index + 1
            byte_index = int_index.to_bytes(4, "little")
        except:
            continue

f.close()
s.close()
