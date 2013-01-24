

import logbot
from axisbox import AABB
from utils import Vector


log = logbot.getlogger("ENTITIES")


class Entity(object):
    def __init__(self, **kwargs):
        self.eid = kwargs["eid"]
        self.x = kwargs["x"]
        self.y = kwargs["y"]
        self.z = kwargs["z"]
        self.velocity = None
        self.is_bot = False

    @property
    def position(self):
        return Vector(self.x / 32.0, self.y / 32.0, self.z / 32.0)

    @property
    def grid_position(self):
        x = self.x / 32
        y = self.y / 32
        z = self.z / 32
        return Vector(x, y, z)


class EntityBot(Entity):
    def __init__(self, **kwargs):
        super(EntityBot, self).__init__(**kwargs)
        self.is_bot = True


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
        self.nbt = kwargs["slotdata"]


class EntityPainting(Entity):
    def __init__(self, **kwargs):
        super(EntityPainting, self).__init__(**kwargs)
        self.title = kwargs["title"]


class Entities(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self.world = dimension.world
        self.entities = {}

    def has_entity(self, eid):
        return eid in self.entities

    def get_entity(self, eid):
        if eid is None:
            return None
        return self.entities.get(eid, None)

    def maybe_commander(self, entity):
        if self.world.commander.eid != entity.eid:
            return
        gpos = entity.grid_position
        block = self.dimension.grid.standing_on_block(AABB.from_player_coords(entity.position))
        if block is None:
            return
        if self.world.commander.last_block is not None and self.world.commander.last_block == block:
            return
        self.world.commander.last_block = block
        #TODO put some nice debug code here
        self.world.commander.last_possition = gpos

    def entityupdate(fn):
        def f(self, *args, **kwargs):
            eid = args[0]
            entity = self.get_entity(eid)
            if entity is None:
                # received entity update packet for entity
                # that was not initialized with new_*, this should not happen
                log.msg("do not have entity id %d registered" % eid)
                return
            if entity.is_bot:
                #log.msg("Server is changing my %s with %s %s" % (fn.__name__, args, kwargs))
                pass
            fn(self, entity, *args[1:], **kwargs)
            self.maybe_commander(entity)
        return f

    def new_bot(self, eid):
        self.entities[eid] = EntityBot(eid=eid, x=0, y=0, z=0)

    def on_new_player(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityPlayer(**kwargs)
        if self.world.commander.name == kwargs["username"]:
            self.world.commander.eid = kwargs["eid"]

    def on_new_dropped_item(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityDroppedItem(**kwargs)

    def on_new_vehicle(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityVehicle(**kwargs)

    def on_new_mob(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityMob(**kwargs)

    def on_new_painting(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityPainting(**kwargs)

    def on_new_experience_orb(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityExperienceOrb(**kwargs)

    def on_destroy(self, eids):
        for eid in eids:
            entity = self.get_entity(eid)
            if entity:
                del self.entities[eid]
                if self.world.commander.eid == eid:
                    self.world.commander.eid = None
            else:
                log.msg('Cannot destroy entity id %d because it is not registered' % eid)

    @entityupdate
    def on_move(self, entity, dx, dy, dz):
        entity.x += dx
        entity.y += dy
        entity.z += dz

    @entityupdate
    def on_look(self, entity, yaw, pitch):
        entity.yaw = yaw
        entity.pitch = pitch

    @entityupdate
    def on_head_look(self, entity, yaw):
        entity.yaw = yaw

    @entityupdate
    def on_move_look(self, entity, dx, dy, dz, yaw, pitch):
        entity.x += dx
        entity.y += dy
        entity.z += dz
        entity.yaw = yaw
        entity.pitch = pitch

    @entityupdate
    def on_teleport(self, entity, x, y, z, yaw, pitch):
        entity.x = x
        entity.y = y
        entity.z = z
        entity.yaw = yaw
        entity.pitch = pitch

    @entityupdate
    def on_velocity(self, entity, dx, dy, dz):
        entity.velocity = (dx, dy, dz)

    @entityupdate
    def on_status(self, entity, status):
        entity.status = status

    @entityupdate
    def on_attach(self, entity, vehicle):
        pass

    @entityupdate
    def on_metadata(self, entity, metadata):
        pass
