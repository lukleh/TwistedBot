

import math
import time
import functools
from collections import namedtuple

from twisted.internet import defer, reactor

import config	
import logbot
			
					
adjacency = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if not (i == j == 0)]
cross = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if ((i == 0) or (j == 0)) and (j != i)]
corners = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if (i != 0) and (j != 0)]

sign = functools.partial(math.copysign, 1)



def do_now(fn, *args, **kwargs):
	do_later(0, fn, *args, **kwargs)


def do_later(delay, fn, *args, **kwargs):
	d = defer.Deferred()
	def fire(ignore):
		return fn(*args, **kwargs)
	d.addCallback(fire)
	d.addErrback(logbot.exit_on_error)
	reactor.callLater(delay, d.callback, None)
	return d


def devnull(body=None):
	pass


def meta2str(meta):
	bins = bin(meta)[2:]
	bins = "0" * (8 - len(bins)) + bins
	return bins

	
def yaw_pitch_between(p1, p2):
	x, y, z = p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2]
	xz = math.hypot(x, z)
	if xz == 0:
		pitch = 0
	else:
		pitch = math.sin(y / xz)
		pitch = math.degrees(pitch)
	if z == 0.0:
		if x > 0:
			yaw = 270
		elif x < 0:
			yaw = 90
	else:
		yaw = math.atan2(-x, z)
		yaw = math.degrees(yaw)
		if yaw < 0:
			yaw = 360 + yaw
	return yaw, -pitch

def grid_shift(v):
	return int(math.floor(v))
		
def standing_pillar(grid, x, y, z):
	for i in xrange(y+1):
		block = grid.get_block(x, i, z)
		log.msg("pillar block %s" % str(block))

def vector_size(tup):
	return math.sqrt(tup[0]*tup[0] + tup[1]*tup[1] + tup[2]*tup[2])


class DirectedGraph(object):
	def __init__(self):
		self.nodes = {}
		self.pred = {}
		self.succ = {}

	@property
	def node_count(self):
		return len(self.nodes)

	@property
	def edge_count(self):
		return len(self.pred) + len(self.succ)
		
	def has_node(self, crd):
		return crd in self.nodes
		
	def get_node(self, crd):
		return self.nodes[crd]
		
	def add_node(self, crd, miny=None):
		if crd not in self.nodes:
			self.nodes[crd] = miny
			self.pred[crd] = {}
			self.succ[crd] = {}
		
	def remove_node(self, crd):
		affected = set()
		del self.nodes[crd]
		for n in self.succ[crd].keys():
			del self.pred[n][crd]
			affected.add(n)
		del self.succ[crd]
		for n in self.pred[crd].keys():
			del self.succ[n][crd]
			affected.add(n)
		del self.pred[crd]
		return affected
				
	def has_edge(self, crd1, crd2):
		return crd2 in self.succ.get(crd1, {})
		
	def get_edge(self, crd1, crd2):
		try:
			return self.succ[crd1][crd2]
		except KeyError:
			return None

	def add_edge(self, crd1, crd2, cost):
		self.succ[crd1][crd2] = cost
		self.pred[crd2][crd1] = cost
		
	def remove_edge(self, crd1, crd2):
		if self.has_edge(crd1, crd2):
			del self.succ[crd1][crd2]
			del self.pred[crd2][crd1]

	def get_succ(self, crd):
		return self.succ[crd].items()


class LLNode(object):
	def __init__(self, previous, next, order, obj):
		self.previous = previous
		self.next = next
		self.order = order
		self.obj = obj


class OrderedLinkedList(object):
	def __init__(self):
		self.pointer = None
		self.head = None
		self.tail = None
		self.length = 0
		self.head_to_tail = True 
		self.reset()

	def __len__(self):
		return self.length

	@property
	def is_empty(self):
		return self.length == 0

	def reset(self):
		self.pointer = self.head

	def add(self, order, obj):
		if self.head is None:
			self.head = LLNode(None, None, order, obj)
			self.pointer = self.head
			self.tail = self.head
			return
		current = self.head
		while True:
			if current.order > order:
				self.insert(current, LLNode(current, current.next, order, obj))
				return
			if current.next is None:
				break
			current = current.next
		self.insert(self.tail, LLNode(self.tail.previous, self.tail, order, obj))

	def remove(self, obj):
		if self.head is None:
			return
		if self.length == 1:
			self.head = None
			self.tail = None
			self.pointer = None
			self.length = 0
			return
		current = self.head
		while True:
			if current.obj == obj:
				if current == self.pointer:
					if current.previous is None:
						self.pointer = current.next
					else:
						self.pointer = current.previous
				if current.previous is None:
					self.head = current.next
					current.next.previous = None
				else:
					current.previous.next = current.next
				if current.next is None:
					self.tail = current.previous
					current.previous.next = None
				else:
					current.next.previous = current.previous
				current.previous = None
				current.next = None
				self.length -= 1
				break
			if current.next is None:
				break
			current = current.next

	def insert(self, spot, item):
		if spot.previous is None:
			n = LLNode(None, spot, item.order, item.obj)
			self.head = n
			spot.previous = n
		elif spot.next is None:
			n = LLNode(spot, None, item.order, item.obj)
			self.tail = n
			spot.next = n
		else:
			spot.next = item
			spot.next.previous = item
		self.length += 1

	def next_circulate(self):
		if self.length < 2:
			return None
		if self.head_to_tail:
			if self.pointer.next is None:
				self.head_to_tail = False
				self.pointer = self.pointer.previous
			else:
				self.pointer = self.pointer.next
		else:
			if self.pointer.previous is None:
				self.head_to_tail = True
				self.pointer = self.pointer.next
			else:
				self.pointer = self.pointer.previous
		return self.current_point()

	def next_rotate(self):
		if self.length < 2:
			return None
		if self.pointer.next is None:
			self.pointer = self.head
		else:
			self.pointer = self.pointer.next
		return self.current_point()

	def current_point(self):
		obj = self.pointer.obj
		return (obj[0], obj[1] - 1, obj[2])