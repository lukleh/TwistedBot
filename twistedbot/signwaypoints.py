

import re
from collections import deque, namedtuple, defaultdict

import logbot
from tools import OrderedLinkedList


log = logbot.getlogger("SIGNS")


Sign = namedtuple('Sign', ['coords', 'value'])

wspace_re = re.compile(ur"\s+")
def normalize_line(line):
	line = line.strip().lower()
	line = wspace_re.sub(" ", line)
	return line


class SignWayPoints(object):
	def __init__(self, navgrid):
		self.navgrid = navgrid
		self.sign_points = {}
		self.crd_to_sign = {}
		self.ordered_sign_groups = defaultdict(OrderedLinkedList)

	def has_name_group(self, group):
		return group in self.ordered_sign_groups

	def has_name_point(self, name):
		return name in self.sign_points
		
	def new(self, crd, value_name, group, last_name):
		n_value_name = normalize_line(value_name)
		try:
			name = last_name
			value = float(n_value_name)
		except ValueError:
			name = n_value_name
			value = None
		if value is not None and group:
			self.ordered_sign_groups[group].add(value, crd)
		if name:
			self.sign_points[name] = crd
		if crd not in self.crd_to_sign:
			msg = "Adding sign: coordinates %s %s '%s' " % (crd, "value" if value is not None else "name", value_name)
			if group:
				msg += "group '%s' " % group
			if last_name:
				msg += "name '%s'" % last_name
			#log.msg(msg)
		self.crd_to_sign[crd] = {"group": group, "name": name}
		
	def remove(self, crd):
		if crd in self.crd_to_sign:
			group = self.crd_to_sign[crd]["group"]
			if group in self.ordered_sign_groups:
				self.ordered_sign_groups[group].remove(crd)
				if self.ordered_sign_groups[group].is_empty:
					del self.ordered_sign_groups[group]
			name = self.crd_to_sign[crd]["name"]
			if name in self.sign_points:
				del self.sign_points[name]

	def get_namepoint(self, name):
		if self.has_name_point(name):
			p = self.sign_points[name]
			return (p[0], p[1] - 1, p[2])
		else:
			return None

	def get_groupnext_rotate(self, group):
		if not self.has_name_group(group):
			return None
		group = self.ordered_sign_groups[group]
		wp = group.current_point()
		if wp is None:
			return None
		while True:
			p = group.next_rotate()
			if p == wp:
				return None
			if self.navgrid.graph.has_node(p):
				return p

	def get_groupnext_circulate(self, group):
		if not self.has_name_group(group):
			return None
		group = self.ordered_sign_groups[group]
		wp = group.current_point()
		if wp is None:
			return None
		n_pass = 0
		while True:
			p = group.next_rotate()
			if p == wp:
				n_pass += 1
				if n_pass == 2:
					return None
			if self.navgrid.graph.has_node(p):
				return p

	def reset_group(self, group):
		if not self.has_name_group(group):
			return
		else:
			self.ordered_sign_groups[group].reset()




