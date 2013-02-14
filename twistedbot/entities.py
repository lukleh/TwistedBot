
import collections

import logbot
import items
import utils
import config
from axisbox import AABB
from utils import Vector


log = logbot.getlogger("ENTITIES")


class Entity(object):
    def __init__(self, eid=None, x=None, y=None, z=None):
        self.eid = eid
        self.x = x
        self.y = y
        self.z = z
        self.velocity = Vector(0, 0, 0)
        self.is_bot = False
        self.is_mob = False
        self.is_player = False
        self.is_xp_orb = False
        self.is_object = False
        self.is_itemstack = False
        self.is_painting = False

    def __hash__(self):
        return self.eid

    def __eq__(self, o):
        return self.eid == o.eid

    def __repr__(self):
        return "EID %d %s" % (self.eid, self.__class__.__name__)

    @property
    def position(self):
        return Vector(self.x / 32.0, self.y / 32.0, self.z / 32.0)

    @property
    def grid_position(self):
        return self.position.grid_shift()

    @property
    def section_position(self):
        return Vector(self.x / 512.0, self.y / 512.0, self.z / 512.0).grid_shift()


class EntityBot(Entity):
    def __init__(self, **kwargs):
        super(EntityBot, self).__init__(**kwargs)
        self.is_bot = True


class EntityLiving(Entity):
    def __init__(self, yaw=None, pitch=None, **kwargs):
        super(EntityLiving, self).__init__(**kwargs)
        self.yaw = yaw
        self.pitch = pitch

    @property
    def orientation(self):
        return (self.yaw, self.pitch)

    @property
    def location(self):
        x, y, z = self.position
        yaw, pitch = self.orientation
        return (x, y, z, yaw, pitch)


class EntityMob(EntityLiving):
    def __init__(self, etype=None, head_yaw=None, velocity_x=None, velocity_y=None, velocity_z=None, metadata=None, **kwargs):
        super(EntityMob, self).__init__(**kwargs)
        self.etype = etype
        self.head_yaw = head_yaw
        self.status = None
        self.is_mob = True
        #TODO assign mob type according to the etype and metadata


class EntityPlayer(EntityLiving):
    width = config.PLAYER_WIDTH
    height = config.PLAYER_HEIGHT

    def __init__(self, world=None, username=None, held_item=None, **kwargs):
        super(EntityPlayer, self).__init__(**kwargs)
        self.username = username
        self.held_item = held_item
        self.is_player = True
        self.commander = None
        if world.commander.name == self.username:
            world.commander.eid = self.eid

    @property
    def position_eyelevel(self):
        return utils.Vector(self.x / 32.0, self.y / 32.0 + config.PLAYER_EYELEVEL, self.z / 32.0)

    @property
    def aabb(self):
        return AABB.from_point_and_dimensions(self.position, self.width, self.height)


class EntityObjectVehicle(Entity):
    def __init__(self, etype=None, object_data=None, velocity=None, **kwargs):
        super(EntityObjectVehicle, self).__init__(**kwargs)
        self.etype = etype
        self.thrower = object_data
        self.is_object = True
        if self.thrower > 0:
            self.vel_x = velocity["x"]
            self.vel_y = velocity["y"]
            self.vel_z = velocity["z"]


class EntityItem(EntityObjectVehicle):
    width = 0.25
    height = 0.25

    def __init__(self, **kwargs):
        super(EntityItem, self).__init__(**kwargs)
        self.is_itemstack = True
        self.itemstack = None

    @property
    def aabb(self):
        return AABB.from_point_and_dimensions(self.position, self.width, self.height)


class EntityExperienceOrb(Entity):
    def __init__(self, count=0, **kwargs):
        super(EntityExperienceOrb, self).__init__(**kwargs)
        self.quantity = count
        self.is_xp_orb = True


class EntityPainting(Entity):
    def __init__(self, title=None, **kwargs):
        super(EntityPainting, self).__init__(**kwargs)
        self.title = title
        self.is_painting = True


class Entities(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self.world = dimension.world
        self.entities = {}
        self.snap_entity2grid = {}
        self.snap_grid2entity = collections.defaultdict(set)

    def in_distance(self, coords, distance=159):
        center_section = (coords / 16.0).grid_shift()
        for crd in utils.grid_sections_around(center_section, distance=distance / 16 + 1):
            if crd in self.snap_grid2entity:
                for ent in self.snap_grid2entity[crd]:
                    yield ent

    def has_entity_eid(self, eid):
        return eid in self.entities

    def get_entity(self, eid):
        if eid is None:
            return None
        return self.entities.get(eid, None)

    def delete_entity(self, eid):
        entity = self.get_entity(eid)
        if entity is not None:
            if entity.eid == self.world.commander.eid:
                self.world.commander.eid = None
            old_sec_pos = self.snap_entity2grid[entity]
            self.snap_grid2entity[old_sec_pos].remove(entity)
            if not self.snap_grid2entity[old_sec_pos]:
                del self.snap_grid2entity[old_sec_pos]
            del self.entities[eid]
            return True
        else:
            #log.msg("deleting %d :(" % eid)
            return False

    def position_updated(self, entity, remove=False):
        old_sec_pos = self.snap_entity2grid[entity]
        sec_pos = entity.section_position
        if old_sec_pos != sec_pos:
            self.snap_entity2grid[entity] = entity.section_position
            self.snap_grid2entity[old_sec_pos].remove(entity)
            #log.msg("E2G change %s %s %s" % (old_sec_pos, sec_pos, entity))
            if not self.snap_grid2entity[old_sec_pos]:
                del self.snap_grid2entity[old_sec_pos]
            self.snap_grid2entity[sec_pos].add(entity)

    def maybe_commander(self, entity):
        if self.world.commander.eid != entity.eid:
            return
        gpos = entity.grid_position
        block = self.dimension.grid.standing_on_block(entity.aabb)
        if block is None:
            return
        if self.world.commander.last_block is not None and self.world.commander.last_block == block:
            return
        self.world.commander.last_block = block
        #TODO put some nice debug code here
        self.world.commander.last_possition = gpos

    def entityupdate(fn):
        def f(self, eid=None, **kwargs):
            entity = self.get_entity(eid)
            if entity is None:
                # received entity update packet for entity that was not initialized with new_*, this should not happen
                log.msg("do not have entity id %d registered" % eid)
                return
            if entity.is_bot:
                # server is trying to change my parameters, like velocity, and I can ignore it :)
                pass
            fn(self, entity, **kwargs)
            self.maybe_commander(entity)
        return f

    def entitynew(fn):
        def f(self, **kwargs):
            entity = fn(self, **kwargs)
            #log.msg("NEW %s" % entity)
            if entity.eid in self.entities:
                #log.msg("DEL FIRST BEFORE NEW ENTITY %s" % entity)
                self.delete_entity(entity.eid)
            self.entities[entity.eid] = entity
            self.snap_entity2grid[entity] = entity.section_position
            self.snap_grid2entity[entity.section_position].add(entity)
        return f

    def new_bot(self, eid):
        self.entities[eid] = EntityBot(eid=eid, x=0, y=0, z=0)

    @entitynew
    def on_new_player(self, **kwargs):
        return EntityPlayer(world=self.world, **kwargs)

    @entitynew
    def on_new_objectvehicle(self, etype=None, **kwargs):
        if etype == 2:
            return EntityItem(**kwargs)
        else:
            return EntityObjectVehicle(etype=etype, **kwargs)

    @entitynew
    def on_new_mob(self, **kwargs):
        return EntityMob(**kwargs)

    @entitynew
    def on_new_painting(self, **kwargs):
        return EntityPainting(**kwargs)

    @entitynew
    def on_new_experience_orb(self, **kwargs):
        return EntityExperienceOrb(**kwargs)

    @entityupdate
    def on_velocity(self, entity, eid=None, x=None, y=None, z=None):
        entity.velocity = Vector(x, y, z)

    def on_destroy(self, eids):
        for eid in eids:
            #log.msg("DESTROY eid %d" % eid)
            if not self.delete_entity(eid):
                #log.msg('Cannot destroy entity id %d because it is not registered' % eid)
                pass

    @entityupdate
    def on_move(self, entity, eid=None, dx=None, dy=None, dz=None):
        entity.x += dx
        entity.y += dy
        entity.z += dz
        self.position_updated(entity)

    @entityupdate
    def on_look(self, entity, eid=None, yaw=None, pitch=None):
        entity.yaw = yaw
        entity.pitch = pitch

    @entityupdate
    def on_move_look(self, entity, eid=None, dx=None, dy=None, dz=None, yaw=None, pitch=None):
        entity.x += dx
        entity.y += dy
        entity.z += dz
        entity.yaw = yaw
        entity.pitch = pitch
        self.position_updated(entity)

    @entityupdate
    def on_teleport(self, entity, eid=None, x=None, y=None, z=None, yaw=None, pitch=None):
        entity.x = x
        entity.y = y
        entity.z = z
        entity.yaw = yaw
        entity.pitch = pitch
        self.position_updated(entity)

    @entityupdate
    def on_head_look(self, entity, eid=None, yaw=None):
        entity.yaw = yaw

    @entityupdate
    def on_status(self, entity, eid=None, status=None):
        entity.status = status

    @entityupdate
    def on_attach(self, entity, eid=None, vehicle_id=None):
        pass

    @entityupdate
    def on_metadata(self, entity, eid=None, metadata=None):
        if entity.is_itemstack:
            slotdata = metadata[10].value
            istack = items.ItemStack.from_slotdata(slotdata)
            entity.itemstack = istack
            log.msg("META %s itemstack %s" % (entity, istack))
