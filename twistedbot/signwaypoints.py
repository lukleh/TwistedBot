

import logbot
import tools


log = logbot.getlogger("SIGNS")


class SignWayPoints(object):
    def __init__(self, navgrid):
        self.navgrid = navgrid
        self.sign_points = {}
        self.crd_to_sign = {}
        self.ordered_sign_groups = {}

    def has_sign_at(self, crd):
        return crd in self.crd_to_sign

    def has_group(self, group):
        return group in self.ordered_sign_groups

    def has_name_point(self, name):
        return name in self.sign_points

    def new(self, sign):
        if sign.is_groupable:
            if sign.group not in self.ordered_sign_groups:
                self.ordered_sign_groups[
                    sign.group] = tools.OrderedLinkedList(name=sign.group)
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
            if self.navgrid.graph.has_node(tools.lower_y(s.coords)):
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
            if self.navgrid.graph.has_node(tools.lower_y(s.coords)):
                return s

    def reset_group(self, group):
        if not self.has_group(group):
            return
        else:
            self.ordered_sign_groups[group].reset()
