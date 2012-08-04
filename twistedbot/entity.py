



class Entity(object):
	def __init__(self, **kwargs):
		self.eid = kwargs["eid"]
		self.x = kwargs["x"]
		self.y = kwargs["y"]
		self.z = kwargs["z"]
		self.velocity = None
		self._isbot = False
		
	@property
	def position(self):
		return (self.x/32.0, self.y/32.0, self.z/32.0) 
		
	@property
	def grid_position(self):
		x = self.x/32
		y = self.y/32
		z = self.z/32
		return (x, y, z)
		
	@property
	def is_bot(self):
		return self._isbot
		
		
class EntityBot(Entity):
	def __init__(self, **kwargs):
		super(EntityBot, self).__init__(**kwargs)
		self._isbot = True
				
class EntityLiving(Entity):
	def __init__(self, **kwargs):
		super(EntityLiving, self).__init__(**kwargs)
		self.yaw = kwargs["yaw"]
		self.pitch = kwargs["pitch"]

	@property
	def orientation(self):
		return (self.yaw, self.pitch)

	@property
	def location(self):
		x, y, z = self.position
		yaw, pitch = self.orientation
		return (x, y, z, yaw, pitch)


class EntityMob(EntityLiving):
	def __init__(self, **kwargs):
		super(EntityMob, self).__init__(**kwargs)
		self.etype = kwargs["etype"]
		self.head_yaw = kwargs["yaw"]
		self.status = None
		#TODO assign mob type according to the etype and metadata
		

class EntityPlayer(EntityLiving):
	def __init__(self, **kwargs):
		super(EntityPlayer, self).__init__(**kwargs)
		self.username = kwargs["username"]
		self.held_item = kwargs["held_item"]


class EntityVehicle(Entity):
	def __init__(self, **kwargs):
		super(EntityVehicle, self).__init__(**kwargs)
		self.etype = kwargs["etype"]
		self.thrower = kwargs["object_data"]
		if self.thrower > 0:
			self.vel_x = kwargs["velocity"]["x"]
			self.vel_y = kwargs["velocity"]["y"]
			self.vel_z = kwargs["velocity"]["z"]
		#TODO assign vehicle type according to the etype and metadata


class EntityExperienceOrb(Entity):
	def __init__(self, **kwargs):
		super(EntityExperienceOrb, self).__init__(**kwargs)
		self.quantity = kwargs["count"]


class EntityDroppedItem(Entity):
	def __init__(self, **kwargs):
		super(EntityDroppedItem, self).__init__(**kwargs)
		self.count = kwargs["count"]
		self.item = kwargs["item"]
		self.data = kwargs["data"]
		#ignoring yaw, pitch and roll for now
