
import re

import logbot
import utils

log = logbot.getlogger("SIGNS")


class Sign(object):
    def __init__(self, coords, line1, line2, line3, line4):
        self.coords = coords
        self.line1 = line1.strip().lower()
        self.line2 = line2.strip().lower()
        self.line3 = line3.strip().lower()
        self.line4 = line4.strip().lower()
        self.value = None
        self.decode()
        self.is_waypoint = self.line1 == "waypoint"
        self.is_groupable = self.group and self.value is not None

    def decode(self):
        self.line2 = re.sub(ur"\s+", " ", self.line2)
        self.line3 = re.sub(ur"\s+", " ", self.line3)
        self.line4 = re.sub(ur"\s+", " ", self.line4)
        try:
            self.name = self.line4
            self.value = float(re.sub(ur",", ".", self.line2))
        except ValueError:
            self.name = self.line2
            self.value = None
        self.group = self.line3

    def __gt__(self, sign):
        return self.value > sign.value

    def __lt__(self, sign):
        return self.value < sign.value

    def __eq__(self, sgn):
        if sgn is None:
            return False
        return self.coords == sgn.coords

    def __str__(self):
        return "$coords:%s group:%s value:%s name:%s$" % (str(self.coords), self.group, self.value, self.name)

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
        sblk = self.dimension.grid.get_block_coords(sign.coords)
        if not sblk.is_sign:
            self.remove(sign.coords)
            return False
        else:
            return self.has_sign_at(sign.coords)

    def has_sign_at(self, crd):
        return crd in self.crd_to_sign

    def has_group(self, group):
        return group in self.ordered_sign_groups

    def has_name_point(self, name):
        return name in self.sign_points

    def new(self, sign):
        if self.has_sign_at(sign.coords):
            self.remove(sign.coords)
        if sign.is_groupable:
            if sign.group not in self.ordered_sign_groups:
                self.ordered_sign_groups[sign.group] = utils.OrderedLinkedList(name=sign.group)
            self.ordered_sign_groups[sign.group].add(sign.value, sign)
        if sign.name:
            self.sign_points[sign.name] = sign
        if sign.coords not in self.crd_to_sign:
            msg = "Adding sign at %s" % str(sign.coords)
            if sign.group:
                msg += " group '%s'" % sign.group
            if sign.value:
                msg += " value '%s'" % sign.value
            if sign.name:
                msg += " name '%s'" % sign.name
            log.msg(msg)
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
        return self.ordered_sign_groups[group].get_by_order(order)

    def get_groupnext_rotate(self, group, current_sign=None, forward_direction=None):
        sgroup = self.ordered_sign_groups[group]
        if current_sign is None:
            return sgroup.first_sign, None
        for sign in sgroup.iter():
            if sign > current_sign:
                return sign, None
        else:
            return sgroup.first_sign, None

    def get_groupnext_circulate(self, group, current_sign=None, forward_direction=True):
        sgroup = self.ordered_sign_groups[group]
        if current_sign is None:
            return sgroup.first_sign, forward_direction
        for sign in sgroup.iter(forward_direction):
            if forward_direction:
                if sign > current_sign:
                    return sign, forward_direction
            else:
                if sign < current_sign:
                    return sign, forward_direction
        else:
            forward_direction = not forward_direction
            for sign in sgroup.iter(forward_direction):
                if forward_direction:
                    if sign > current_sign:
                        return sign, forward_direction
                else:
                    if sign < current_sign:
                        return sign, forward_direction
