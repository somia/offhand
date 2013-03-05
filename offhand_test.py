import asyncore
import os
import random
import socket
import subprocess
import sys
import threading
import time

import offhand

messages = [
	# TestSequence
	["\xf0\x00\x0d"],
	[],
	["", "\xde\xad\xbe\xef\xca\xfe\xba", "", "", "\xbe", ""],

	# TestParallel
	["\xff\xee\xdd"],
	[],
	["", "\xcc\xcc\xcc\xbb\xbb\xbb\xaa", "", "", "\xaa", ""],
]

class Puller(offhand.AsynConnectPuller):

	class Node(offhand.AsynConnectPuller.Node):
		socket_family = socket.AF_UNIX

	def handle_pull(self, node, message, commit):
		with commit:
			if random.randint(0, 1):
				print self, node, "engage", message
				commit.engage()
				messages.remove(message)
			else:
				print self, node, "cancel", message

def test(done, score):
	os.chdir(".test/sockets")

	with Puller() as p1, Puller() as p2:
		pullers = p1, p2

		for i in xrange(3):
			for p in pullers:
				p.connect(str(i))

		timeout   = 0.1
		last_time = time.time()

		while True:
			t = timeout - (time.time() - last_time)
			if t <= 0:
				for p in pullers:
					p.reconnect()

				last_time = time.time()
				t = timeout

			if asyncore.socket_map:
				asyncore.loop(timeout=t, use_poll=True, count=1)
			elif done[0]:
				break
			else:
				time.sleep(t)

		count = 0.0

		for p in pullers:
			for n in p.nodes:
				print "Node:", n.stats
				count += 1

		print "Avg:", sum((p.stats for p in pullers), offhand.Stats()) / count

	score[0] += 1

def main():
	done  = [False]
	score = [0]

	t = threading.Thread(target=test, args=(done, score))
	t.daemon = True

	p = subprocess.Popen(["./offhand.test", "-test.v=true"])
	try:
		t.start()
	finally:
		status = p.wait()
		if status == 0:
			print "go test exited"
			score[0] += 1
		else:
			print >>sys.stderr, "go test exited with %r" % status

	done[0] = True
	t.join(2)
	if t.is_alive():
		print >>sys.stderr, "python test exit timeout"
	else:
		print "python test exited"

		if messages:
			print >>sys.stderr, "remaining messages:"
			for m in messages:
				print >>sys.stderr, "  %r" % m
		else:
			score[0] += 1

	if score[0] != 3:
		sys.exit(1)

if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print
