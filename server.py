import socket
import sys
PORT = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('', PORT))
j = 1

while True:
	data, addr = s.recvfrom(1024)
	if j == int.from_bytes(data[0:3], "little"):
		print(str(data[4:100], 'utf-8'), end="")
		j = j + 1
	s.sendto(data.upper(), addr)

