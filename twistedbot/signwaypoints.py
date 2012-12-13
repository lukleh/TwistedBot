
import re

import logbot
import utils
import gridspace

log = logbot.getlogger("SIGNS")


class Sign(object):
    def __init__(self, coords, line1, line2, line3, line4):
        self.coords = coords
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self.line4 = line4
        self.is_waypoint = line1.strip().lower() == "waypoint"
        self.decode()
        self.is_groupable = self.group and self.value is not None
        self.nav_coords = self.coords.offset(dy=-1)

    def decode(self):
        self.line2 = re.sub(ur"\s+", " ", self.line2.strip().lower())
        try:
            self.name = self.line4
            self.value = float(re.sub(ur",", ".", self.line2))
        except ValueError:
            self.name = self.line2
            self.value = None
        self.group = self.line3

    def __eq__(self, sgn):
        return self.coords == sgn.coords

    def __str__(self):
        return "$coords:%s group:%s value:%s name:%s$" % \
            (str(self.coords), self.group, self.value, self.name)

    def __repr__(self):
        return self.__str__()


class SignWayPoints(object):
    def __init__(self, dimension):
        self.dimension = dimension
        self.sign_points = {}
        self.crd_to_sign = {}
        self.ordered_sign_groups = {}

    def on_new_sign(self, x, y, z, line1, line2, line3, line4):
        sign = Sign(utils.Vector(x, y, z), line1, line2, line3, line4)
        if sign.is_waypoint:
            self.new(sign)

    def check_sign(self, sign):
        crd = sign.coords
        sblk = self.dimension.grid.get_block(crd[0], crd[1], crd[2])
        if not sblk.is_sign:
            self.remove(crd)
            return False
        else:
            return self.sign_waypoints.has_sign_at(crd)

    def has_sign_at(self, crd):
        return crd in self.crd_to_sign

    def has_group(self, group):
        return group in self.ordered_sign_groups

    def has_name_point(self, name):
        return name in self.sign_points

    def new(self, sign):
        if sign.is_groupable:
            if sign.group not in self.ordered_sign_groups:
                self.ordered_sign_groups[sign.group] = utils.OrderedLinkedList(name=sign.group)
            self.ordered_sign_groups[sign.group].add(sign.value, sign)
        if sign.name:
            self.sign_points[sign.name] = sign
        if sign.coords not in self.crd_to_sign:
            msg = "Adding sign: coordinates %s" % str(sign.coords)
            if sign.group:
                msg += "group '%s' " % sign.group
            if sign.value:
                msg += "value '%s' " % sign.value
            if sign.name:
                msg += "name '%s'" % sign.name
            #log.msg(msg)
        self.crd_to_sign[sign.coords] = sign

    def remove(self, crd):
        if crd in self.crd_to_sign:
            sign = self.crd_to_sign[crd]
            if sign.group in self.ordered_sign_groups:
                self.ordered_sign_groups[sign.group].remove(sign)
                if self.ordered_sign_groups[sign.group].is_empty:
                    del self.ordered_sign_groups[sign.group]
            if sign.name in self.sign_points:
                del self.sign_points[sign.name]

    def get_namepoint(self, name):
        if self.has_name_point(name):
            s = self.sign_points[name]
            return s
        else:
            return None

    def get_name_from_group(self, name):
        group, _, order = name.rpartition(' ')
        if not self.has_group(group):
            return None
        try:
            order = float(order)
        except ValueError:
            return None
        sgroup = self.ordered_sign_groups[group]
        for o in sgroup.iter():
            if o.order == order:
                return o.obj
        return None

    def get_groupnext_rotate(self, group):
        if not self.has_group(group):
            return None
        sgroup = self.ordered_sign_groups[group]
        cs = sgroup.current_point()
        if cs is None:
            sgroup.start()
            return sgroup.current_point()
        while True:
            s = sgroup.next_rotate()
            if s == cs:
                return None
            if gridspace.can_stand(s.coords):
                return s

    def get_groupnext_circulate(self, group):
        if not self.has_group(group):
            return None
        sgroup = self.ordered_sign_groups[group]
        cs = sgroup.current_point()
        if cs is None:
            sgroup.start()
            return sgroup.current_point()
        n_pass = 0
        while True:
            s = sgroup.next_circulate()
            if s == cs:
                n_pass += 1
                if n_pass == 2:
                    return None
            if gridspace.can_stand(s.coords):
                return s

    def reset_group(self, group):
        if not self.has_group(group):
            return
        else:
            self.ordered_sign_groups[group].reset()
