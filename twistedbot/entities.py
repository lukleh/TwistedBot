

import logbot
from gridspace import GridSpace
from axisbox import AABB


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
        return (self.x / 32.0, self.y / 32.0, self.z / 32.0)

    @property
    def grid_position(self):
        x = self.x / 32
        y = self.y / 32
        z = self.z / 32
        return (x, y, z)


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

    @property
    def aabb(self):
        return AABB.from_player_coords(self.position)


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


class Entities(object):
    def __init__(self, world):
        self.world = world
        self.entities = {}

    def has_entity(self, eid):
        return eid in self.entities

    def get_entity(self, eid):
        e = self.entities.get(eid, None)
        if e is None:
            log.msg("Entity %d not in mobs list" % eid)
        return e

    def maybe_commander(self, entity):
        if self.world.commander.eid != entity.eid:
            return
        gpos = entity.grid_position
        block = self.world.grid.standing_on_block(
            AABB.from_player_coords(entity.position))
        if block is None:
            return
        if self.world.commander.last_block is not None and self.world.commander.last_block == block:
            return
        self.world.commander.last_block = block
        lpos = self.world.commander.last_possition
        in_nodes = self.world.navgrid.graph.has_node(block.coords)
        gs = GridSpace(self.world.grid, block=block)
        msg = "P in nm %s nm nodes %d\n" % \
            (in_nodes, self.world.navgrid.graph.node_count)
        msg += "gs_stand %s\n" % str(gs.bb_stand)
        msg += str(block) + '\n'
        msg += str(block.grid_bounding_box)
        try:
            msg += "\nsucessors %s" % str(self.world.navgrid.graph.get_succ(block.coords))
        except:
            pass
        if lpos is not None:
            gsl = GridSpace(self.world.grid, coords=lpos)
            if gsl.can_stand_on:
                pass
            else:
                gsl = GridSpace(
                    self.world.grid, coords=(lpos[0], lpos[1] - 1, lpos[2]))
                if gsl.can_stand_on:
                    lpos = gsl.coords
            if not(gsl.bb_stand is None or gs.bb_stand is None):
                msg += "\ncost from %s to %s %s\n" % \
                    (lpos, block.coords,
                     self.world.navgrid.graph.get_edge(lpos, block.coords))
                msg += "last stand %s now stand %s from %s to %s\n" % \
                    (gsl.can_stand_on, gs.can_stand_on,
                     gsl.bb_stand, gs.bb_stand)
                if gsl.can_go_between(gs, debug=True):
                    msg += "can go True with cost %s\n" % gsl.edge_cost
                else:
                    msg += "can go False\n"
                msg += "can stand between %s intersection %s" % (
                    gsl.can_stand_between(gs, debug=True), gsl.intersection)

        log.msg(msg)
        self.world.commander.last_possition = gpos

    def entityupdate(fn):
        def f(self, *args, **kwargs):
            eid = args[0]
            entity = self.get_entity(eid)
            if entity is None:
                # received entity update packet for entity
                # that was not initialized with new_*, this should not happen
                log.msg("do not have entity %d registered" % eid)
                return
            if entity.is_bot:
                #log.msg("Server is changing my %s" % fn.__name__)
                        #(fn.__name__, args, kwargs))
                pass
            fn(self, entity, *args[1:], **kwargs)
            self.maybe_commander(entity)
        return f

    def new_bot(self, eid):
        self.entities[eid] = EntityBot(eid=eid, x=0, y=0, z=0)

    def new_mob(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityMob(**kwargs)

    def new_player(self, **kwargs):
        self.entities[kwargs["eid"]] = EntityPlayer(**kwargs)
        if self.world.commander.name == kwargs["username"]:
            self.world.commander.eid = kwargs["eid"]

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
                if self.world.commander.eid == eid:
                    self.world.commander.eid = None

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
