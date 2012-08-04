

import math
import time

import config	
					
					
adjacency = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if not (i == j == 0)]
cross = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if ((i == 0) or (j == 0)) and (j != i)]
corners = [(i,j) for i in (-1,0,1) for j in (-1,0,1) if (i != 0) and (j != 0)]


def devnull(body=None):
	pass


def time_jump_to(h):
	#1/2at^2 + v*t - h= 0
	return (-config.SPEED_JUMP + math.sqrt(config.SPEED_JUMP*config.SPEED_JUMP - 4*0.5*config.G*(-h))) / (config.G)
	
	
def time_jump_onto(h):
	try:
		return (-config.SPEED_JUMP - math.sqrt(config.SPEED_JUMP*config.SPEED_JUMP - 4*0.5*config.G*(-h))) / (config.G)
	except:
		log.err(_why="time_jump_onto %s" % str(h))
		raise
	
	
def time_fall_to(h):
	#1/2*a*t^2 = h
	return math.sqrt(h*2/(-config.G))
	
	
def move_cost(elevation=0):
	if elevation < 0:
		return time_fall_to(-elevation) + config.COST_DIRECT
	elif elevation > 0:
		return time_jump_onto(elevation) + config.COST_DIRECT
	
	
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


def aabb_in_blocks(grid, bb):
	out = []
	for x, y, z in bb.grid_corners:
		b = grid.get_block(x, y, z)
		if b is not None:
			out.append(b)
	return out

	
def aabb_in_chunks(grid, bb):
	chunk_coords = set()
	for x, _, z in bb.grid_corners:
		chunk_coords.add((x >> 4, z >> 4))
	return [grid.get_chunk(coord) for coord in chunk_coords]
	
def chunks_complete(chunks):
	for chunk in chunks:
		if chunk is None:
			return False
		elif chunk.complete == False:
			return False
	return True

	
def grid_shift(v):
	if v < 0:
		return int(v) - 1
	else:
		return int(v)

		
def standing_pillar(grid, x, y, z):
	for i in xrange(y+1):
		block = grid.get_block(x, i, z)
		log.msg("pillar block %s" % str(block))


def axis_direction_from_ds(dx=None, dy=None, dz=None):
	if dx is not None and dx != 0:
		axis = 0
		direction = dx
	elif dy is not None and dy != 0:
		axis = 1
		direction = dy
	elif dz is not None and dz != 0:
		axis = 2
		direction = dz
	if direction == 0:
		raise Exception("direction cannot be 0")
	return axis, direction


def block_collision_distance(block, bb, dx=None, dy=None, dz=None):
	axis, direction = axis_direction_from_ds(dx, dy, dz)
	dists = [bb.collision_distance(block_b, axis, direction) for block_b in block.grid_bounding_boxes]
	real_d = [d for d in dists if d is not None]
	if len(real_d) > 0:
		return min(real_d)
	else:
		return None


def blocks_collision_distance(blocks, bb, dx=0, dy=0, dz=0):
	dists = [block_collision_distance(block, bb, dx=dx, dy=dy, dz=dz) for block in blocks]
	real_dists = [d for d in dists if d is not None]
	if len(real_dists) > 0:
		return min(real_dists)
	else:
		return None
		
		
def directional_collision_distance(grid, bb, dx=0, dy=0, dz=0):
	sbb = bb.extend_to(dx=dx, dy=dy, dz=dz)
	sblocks = aabb_in_blocks(grid, sbb)
	d = blocks_collision_distance(sblocks, bb, dx=dx, dy=dy, dz=dz)
	return d


def standing_on_solidblock(grid, bb, grid_pos):
	standing_on = None
	da = -1
	sbb = bb.extend_to(dy=da)
	blocks = aabb_in_blocks(grid, sbb)
	d = blocks_collision_distance(blocks, bb, dy=da)
	if d is None or d != 0:
		return None
	for block in blocks:
		cur_d = block_collision_distance(block, bb, dy=da)
		if cur_d == d:
			standing_on = block
			if standing_on.x == grid_pos[0] and standing_on.z == grid_pos[2]:
				break
	return standing_on


def gravity_displ(vel):
	d = config.TIME_STEP * vel
	d += 0.5 * config.G * pow(config.TIME_STEP, 2)
	vel += config.G * config.TIME_STEP
	return d, vel 

