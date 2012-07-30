

class GridSpace(object):
	def __init__(self, grid, coords):
		self.coords
		self.ground_block = self.grid.get_block_coords(coords)
		self.legs_block = None
		self.head_block = None
		self._canstand = None
		

	def __hash__(self):
		return hash(self.coords)
		
	@property
	def cost(self):
		return self.cost_to_other

	def can_stand(self):
		if self._canstand is None:
			if not self.ground_block.is_solid:
				self._canstand = False
				return self._canstand
			elif self.legs_block.is_solid:
				self._canstand = False
			elif not self.head_block.is_solid:
				self._canstand = False

	def standing_at_space(self):
		raise NotImplementedError

	def as_meshnode(self):
		raise NotImplementedError
		
	def can_go(self, other_space):
		raise NotImplementedError
