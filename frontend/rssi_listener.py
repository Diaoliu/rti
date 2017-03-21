#!/usr/bin/env python

import sys
import lib.tos as tos

# read the message from serial port
# convert to suitable format
# save into global variable "nodes"
def read_serial():
	if len(sys.argv) < 2:
		print "Usage:", sys.argv[0], "/dev/ttyUSB0"
		sys.exit()
	# call the driver
	s = tos.Serial(sys.argv[1], 115200)

	while True:
		# read a line
		p = s.read()
		ack = tos.AckFrame(p.data)
		if ack.protocol != s.SERIAL_PROTO_ACK:
			ampkt = tos.ActiveMessage(tos.NoAckDataFrame(p.data).data)
			sys.stdout.write("".join([chr(i) for i in ampkt.data]).strip('\0'))

if __name__ == "__main__":

	if '-h' in sys.argv:
		print "Usage:", sys.argv[0], "serial@/dev/ttyUSB0"
		sys.exit()

	read_serial()
