


import config
import logbot
from entity import EntityMob, EntityPlayer, EntityVehicle, EntityExperienceOrb, EntityDroppedItem


log = logbot.getlogger("ENTITIES")


class Entities(object):
	def __init__(self, world):
		self.world = world
		self.entities = {}

	def get_entity(self, eid):
		if eid in self.entities:
			return self.entities[eid]
		else:
			#log.msg("Entity %d not in mobs list" % eid)
			return None

	def maybe_commander(self, entity):
		if self.world.bot.commander.eid != entity.eid: return
		gpos = entity.grid_position
		if self.world.bot.commander.last_possition == gpos:
			return
		self.world.bot.commander.last_possition = gpos
		block = self.world.grid.get_block(gpos[0], gpos[1] - 1, gpos[2]) #TODO this will not work all the time, entity can stand "in" block (soul sand, lilly pad, etc.
		if block is None: return
		if not block.is_solid: return
		in_nodes = self.world.navmesh.graph.has_node(block.coords)
		log.msg("Player in navmesh %s on %s navmesh nodes %d" % (in_nodes, block, len(self.world.navmesh.graph.nodes)))

	def entityupdate(fn):
		def f(self, *args, **kwargs):
			eid = args[0]
			entity = self.get_entity(eid)
			if entity is None: 
				#received entity update packet for entity that was not initialized with new_*, this should not happen 
				log.msg("do not have entity %d registered" % eid)
				return
			if entity.is_bot:
				log.msg("Server is changing me with %s %s %s" % (fn.__name__, args, kwargs))
			fn(self, entity, *args[1:], **kwargs)
			#self.maybe_commander(entity)
		return f

	def new_mob(self, **kwargs):
		self.entities[kwargs["eid"]] = EntityMob(**kwargs)

	def new_player(self, **kwargs):
		self.entities[kwargs["eid"]] = EntityPlayer(**kwargs)
		if self.world.bot.commander.name == kwargs["username"]:
			self.world.bot.commander.eid = kwargs["eid"]

	def new_dropped_item(self, **kwargs):
		self.entities[kwargs["eid"]] = EntityDroppedItem(**kwargs)

	def new_vehicle(self, **kwargs):
		self.entities[kwargs["eid"]] = EntityVehicle(**kwargs)

	def new_experience_orb(self, **kwargs):
		self.entities[kwargs["eid"]] = EntityExperienceOrb(**kwargs)

	def destroy(self, eids):
		for eid in eids:
			entity = self.get_entity(eid)
			if entity: 
				del self.entities[eid]
				if self.world.bot.commander.eid == eid:
					self.world.bot.commander.eid = None

	@entityupdate
	def move(self, entity, dx, dy, dz):
		entity.x += dx 
		entity.y += dy 
		entity.z += dz 

	@entityupdate
	def look(self, entity, yaw, pitch):
		entity.yaw = yaw 
		entity.pitch = pitch

	@entityupdate
	def head_look(self, entity, yaw):
		entity.yaw = yaw

	@entityupdate
	def move_look(self, entity, dx, dy, dz, yaw, pitch):
		entity.x += dx
		entity.y += dy 
		entity.z += dz 
		entity.yaw = yaw 
		entity.pitch = pitch 

	@entityupdate
	def teleport(self, entity, x, y, z, yaw, pitch):
		entity.x = x
		entity.y = y
		entity.z = z
		entity.yaw = yaw 
		entity.pitch = pitch 

	@entityupdate
	def velocity(self, entity, dx, dy, dz):
		entity.velocity = (dx, dy, dz) 

	@entityupdate
	def status(self, entity, status):
		entity.status = status 

	@entityupdate
	def attach(self, entity, vehicle):
		pass 

	@entityupdate
	def metadata(self, entity, metadata):
		pass

