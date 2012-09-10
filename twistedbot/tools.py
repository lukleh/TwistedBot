

import math
import time
import functools

import config	
					
					
adjacency = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if not (i == j == 0)]
cross = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if ((i == 0) or (j == 0)) and (j != i)]
corners = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if (i != 0) and (j != 0)]

sign = functools.partial(math.copysign, 1)


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

