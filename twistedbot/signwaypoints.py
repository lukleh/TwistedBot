

import re
from collections import deque, namedtuple, defaultdict

import logbot



log = logbot.getlogger("SIGNS")


Sign = namedtuple('Sign', ['coords', 'value'])

wspace_re = re.compile(ur"\s+")
def normalize_line(line):
	line = line.strip().lower()
	line = wspace_re.sub(" ", line)
	return line


class SignWayPoints(object):
	def __init__(self, navmesh):
		self.navmesh = navmesh
		self.sign_points = {}
		self.crd_to_sign = {}
		self.ordered_sign_groups = defaultdict(OrderedWayPoints)

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
			self.ordered_sign_groups[group].add(crd, value)
		if name:
			self.sign_points[name] = crd
		if False and crd not in self.crd_to_sign:
			msg = "Adding sign: coordinates %s %s '%s' " % (crd, "value" if value is not None else "name", value_name)
			if group:
				msg += "group '%s' " % group
			if last_name:
				msg += "name '%s'" % last_name
			log.msg(msg)
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

	def get_groupnext(self, group):
		if group is not None:
			return self.get_next_from_group(group)
		else:
			return None

	def get_next_from_group(self, group):
		if not self.has_name_group(group):
			return None
		wp = self.ordered_sign_groups[group].get_next_sign()
		if wp is None:
			return None
		if self.navmesh.graph.has_node(wp):
			return wp
		wp_idx = self.ordered_sign_groups[group].next_waypoint_index
		for _ in xrange(len(self.ordered_sign_groups[group])):
			wp = self.ordered_sign_groups[group].get_next_sign()
			if self.navmesh.graph.has_node(wp):
				return wp
			if self.ordered_sign_groups[group].next_waypoint_index == wp_idx:
				return None

	def get_groupnext_circulate(self, group):
		if not self.has_name_group(group):
			return None
		wp = self.ordered_sign_groups[group].get_circulate_sign()
		if wp is None:
			return None
		if self.navmesh.graph.has_node(wp):
			return wp
		wp_idx = self.ordered_sign_groups[group].next_waypoint_index
		npass = 0
		for _ in xrange(len(self.ordered_sign_groups[group])*2):
			wp = self.ordered_sign_groups[group].get_circulate_sign()
			if self.navmesh.graph.has_node(wp):
				return wp
			if self.ordered_sign_groups[group].next_waypoint_index == wp_idx:
				npass += 1
				if npass == 2:
					return None

	def reset_group(self, group):
		if not self.has_name_group(group):
			return
		else:
			self.ordered_sign_groups[group].reset()


class OrderedWayPoints(object):
	def __init__(self):
		self.ordered_waypoints = deque()
		self.reset()

	def __len__(self):
		return len(self.ordered_waypoints)

	def reset(self):
		self.next_waypoint = None
		self.next_waypoint_index = None
		self.direction = 1
			
	def waypoint_index(self, crd):
		for i, w in enumerate(self.ordered_waypoints):
			if w.coords == crd:
				return i
		return None

	@property
	def is_empty(self):
		return len(self.ordered_waypoints) == 0
			
	def add(self, crd, value):
		sign = Sign(crd, value)
		for i, owp in enumerate(self.ordered_waypoints):
			if owp.coords == sign.coords:
				if owp.value != sign.value:
					self.ordered_waypoints.pop(i)
					log.msg("Sign different value, replace at %s" % str(crd))
					break
				else:
					return
		self.ordered_waypoints.append(sign)
		self.sort_ordered()
		self.next_waypoint_index = self.waypoint_index(self.next_waypoint)
		if self.next_waypoint is None:
			self.get_next_sign()
			
	def remove(self, crd):
		if crd == self.next_waypoint:
			self.get_next_sign()
		owp = self.ordered_waypoints.pop(self.waypoint_index(crd))
		self.sort_ordered()
		self.next_waypoint_index = self.waypoint_index(self.next_waypoint)

	def sort_ordered(self):
		self.ordered_waypoints = sorted( self.ordered_waypoints, key=lambda s: s.value)
			
	def get_next_sign(self):
		if len(self.ordered_waypoints) < 2:
			self.next_waypoint = None
			self.next_waypoint_index = None
			return None
		if self.next_waypoint is None:
			self.next_waypoint = self.ordered_waypoints[0].coords
			self.next_waypoint_index = 0
		else:
			self.next_waypoint_index += 1
			if self.next_waypoint_index >= len(self.ordered_waypoints):
				self.next_waypoint_index = 0
			self.next_waypoint = self.ordered_waypoints[self.next_waypoint_index].coords
		return (self.next_waypoint[0], self.next_waypoint[1] - 1, self.next_waypoint[2])

	def get_circulate_sign(self):
		if len(self.ordered_waypoints) < 2:
			self.next_waypoint = None
			self.next_waypoint_index = None
			return None
		if self.next_waypoint is None:
			self.next_waypoint = self.ordered_waypoints[0].coords
			self.next_waypoint_index = 0
		else:
			self.next_waypoint_index += self.direction
			if self.next_waypoint_index >= len(self.ordered_waypoints):
				self.direction *= (-1)
				self.next_waypoint_index -= 2
			elif self.next_waypoint_index < 0:
				self.direction *= (-1)
				self.next_waypoint_index += 2
			self.next_waypoint = self.ordered_waypoints[self.next_waypoint_index].coords
		return (self.next_waypoint[0], self.next_waypoint[1] - 1, self.next_waypoint[2])

