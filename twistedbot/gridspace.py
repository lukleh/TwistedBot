
from math import copysign

import fops
import logbot
import blocks
import config
from aabb import AABB


log = logbot.getlogger("GRIDSPACE")


class GridSpace(object):

	def __init__(self, grid, coords=None, block=None, bb=None):
		self.grid = grid
		if block is not None:
			self.block = block
			self.coords = self.block.coords
		elif coords is not None:
			self.coords = coords
			self.block = self.grid.get_block(coords[0], coords[1], coords[2])
		elif bb is not None:
			self.bb_stand = bb
			self.block = self.grid.standing_on_solidblock(bb)
			self.coords = self.block.coords
		else:
			raise Exception("Empty gridspace object")
		self.blocks3 = (self.block, 
						self.grid.get_block(self.coords[0], self.coords[1] + 1, self.coords[2]),
						self.grid.get_block(self.coords[0], self.coords[1] + 2, self.coords[2]))
		self.bb_stand = None
		self.stand_block = None
		self.intersection = None
		self.can_stand_on = self._can_stand_on()

	def __unicode__(self):
		return unicode(self.block)

	def __str__(self):
		return unicode(self)

	def __eq__(self, other):
		return self.coords == other.coords

	@property
	def b3(self):
		return "%s %s" % (self.block.coords, ", ".join([b.name for b in self.blocks3]))

	@classmethod
	def blocks_to_avoid(cls, blks):
		for b in blks:
			if isinstance(b, blocks.Cobweb) or isinstance(b, blocks.Fire) or isinstance(b, blocks.Cactus) or isinstance(b, blocks.BlockFluid):
				return True
		else:
			return False

	def _can_stand_on(self):
		"""
		can stand on top of the center of the block
		"""
		under = self.grid.get_block(self.coords[0], self.coords[1] - 1, self.coords[2])
		if self.block.has_vertical_movement:
			bb = AABB.from_block_coords(self.block.coords)
			if (under.is_fence and under.collidable):
				self.bb_stand = bb.shift(min_y=under.grid_bounding_box.max_y)
			else:
				self.bb_stand = bb
			if self.blocks_to_avoid(self.grid.blocks_in_aabb(self.bb_stand)):
				return False
			if self.grid.aabb_collides(self.bb_stand):
				return False
			self.stand_block = self.block
			self.platform = self.bb_stand.set_to(max_y=self.bb_stand.min_y)
			return True
		if not self.block.collidable and not (under.is_fence and under.collidable):
			return False
		if self.blocks_to_avoid([self.block]):
			return False
		if under.is_fence and under.collidable:
			fence_top = under.maxedge_platform(y=1)
			if self.block.collidable:
				self.platform = self.block.maxedge_platform(y=1)
				self.stand_block = self.block
				if fence_top.min_y > self.platform.min_y:
					self.platform = fence_top
					self.stand_block = under
			else:
				self.platform = fence_top
				self.stand_block = under
		else:
			self.platform = self.block.maxedge_platform(y=1)
			self.stand_block = self.block
		bb = AABB.from_block_coords(self.block.coords)
		self.bb_stand = bb.offset(dy=self.platform.min_y - bb.min_y)
		if bb.collides_on_axes(self.platform, x=True, z=True):
			if self.grid.aabb_collides(self.bb_stand):
				return False
			elif self.blocks_to_avoid(self.grid.blocks_in_aabb(self.bb_stand)):
				return False
			else:
				return True
		else:
			return False

	def can_go(self, gs, update_to_bb_stand=False):
		if not self.can_stand_between(gs):
			return False
		if not self.can_go_between(gs, update_to_bb_stand=update_to_bb_stand):
			return False
		return True

	def can_stand_between(self, gs, debug=False):
		if self.block.has_vertical_movement or gs.block.has_vertical_movement:
			return True
		if fops.gt(abs(self.platform.min_y - gs.platform.min_y), config.MAX_STEP_HEIGHT):
			return True
		stand_platform = self.platform.expand(config.PLAYER_BODY_DIAMETER - 0.09, 0, config.PLAYER_BODY_DIAMETER - 0.09)
		self.intersection = gs.stand_block.intersection_on_axes(stand_platform, x=True, z=True, debug=debug)
		if self.intersection is None:
			return False
		if self.stand_block.x != gs.stand_block.x and self.stand_block.z != gs.stand_block.z:
			if fops.lt(gs.platform.get_side('min', x=True, z=True), 0.5):
				return False
			else:
				return True
		else:
			return True

	def can_go_between(self, gs, update_to_bb_stand=False, debug=False):
		edge_cost = 0
		bb_stand = self.bb_stand
		other_bb_stand	= gs.bb_stand
		if self.grid.aabb_on_ladder(self.bb_stand):
			if fops.gt(other_bb_stand.min_y, self.bb_stand.min_y):
				if not self.grid.aabb_on_ladder(bb_stand.shift(min_y=other_bb_stand.min_y)):
					return False
		if fops.gt(bb_stand.min_y, other_bb_stand.min_y):
			elev = bb_stand.min_y - other_bb_stand.min_y
			elev_bb = other_bb_stand.extend_to(dy=elev)
			bb_from = bb_stand
			bb_to = other_bb_stand.offset(dy=elev)
		elif fops.lt(bb_stand.min_y, other_bb_stand.min_y):
			elev = other_bb_stand.min_y - bb_stand.min_y
			if fops.gt(elev, config.MAX_JUMP_HEIGHT):
				return False
			if fops.lte(elev, config.MAX_STEP_HEIGHT):
				elev = config.MAX_STEP_HEIGHT
				aabbs = self.grid.aabbs_in(bb_stand.extend_to(0, elev, 0))
				for bb in aabbs:
					elev = bb_stand.calculate_axis_offset(bb, elev, 1)
			elev_bb = bb_stand.extend_to(dy=elev)
			bb_from = bb_stand.offset(dy=elev)
			bb_to = other_bb_stand
		else:
			elev = 0
			elev_bb = None
			bb_from = bb_stand
			bb_to = other_bb_stand
		if elev_bb is not None:
			if self.grid.aabb_collides(elev_bb):
				return False
			if self.blocks_to_avoid(self.grid.blocks_in_aabb(elev_bb)):
				return False
		if self.grid.collision_between(bb_from, bb_to, debug=debug):
			return False
		if self.blocks_to_avoid(self.grid.passing_blocks_between(bb_from, bb_to)):
			return False
		if fops.lte(elev, config.MAX_STEP_HEIGHT) and fops.gte(elev, -config.MAX_STEP_HEIGHT):
			edge_cost += config.COST_DIRECT * bb_from.horizontal_distance_to(bb_to)
		else:
			edge_cost += config.COST_FALL * bb_from.horizontal_distance_to(bb_to)
			vd = bb_from.horizontal_distance_to(bb_to)
			if vd < 0:
				edge_cost += config.COST_FALL * vd
			else:
				edge_cost += config.COST_CLIMB * vd
		self.edge_cost = edge_cost
		if update_to_bb_stand:
			gs.bb_stand = other_bb_stand
		return True