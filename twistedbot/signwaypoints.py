

from collections import deque




class SignWayPoints(object):
	def __init__(self, navmesh):
		self.navmesh = navmesh
		self.signs = {}
		self.ordered = OrderedWayPoints()
		
	def new(self, crd, value, name):
		log.msg("Add sign: coordinates %s value %s group %s" %(crd, value, name))
		self.signs[crd] = {"value": value, "name": name} 
		self.ordered.add(crd, value)

	def remove(self, crd):
		if crd in self.signs:
			log.msg("Remove sign: coordinates %s value %s group %s" %(crd, self.signs[crd]["value"], self.signs[crd]["name"]))
			del self.signs[crd]
			self.ordered.remove(crd)

	@property
	def next_waypoint(self):
		wp = self.ordered.get_next_sign()
		if wp is None:
			return wp
		wp_idx = self.ordered.next_waypoint_index
		for i in len(self.ordered_waypoints):
			wp = self.ordered.get_next_sign()
			if wp in self.navmesh.graph.has_node(wp):
				return wp
			if self.ordered.next_waypoint_index == wp_idx:
				return None


class OrderedWayPoints(object):
	def __init__(self):
		self.ordered_waypoints = deque()
		self.next_waypoint = None
		self.next_waypoint_index = None
			
	def waypoint_index(self, crd):
		for i, w in enumerate(self.ordered_waypoints):
			if w[1] == crd:
				return i
		return None
			
	def add(self, crd, value):
		log.msg("Adding %s with value %s to ordered waypoints" % (str(crd), value))
		self.ordered_waypoints.append((value, crd))
		self.sort_ordered()
		self.next_waypoint_index = self.waypoint_index(self.next_waypoint)
		if self.next_waypoint is None:
			self.get_next_waypoint()
			
	def remove(self, crd):
		if crd == self.next_waypoint:
			self.get_next_waypoint()
		owp = self.ordered_waypoints.pop(self.waypoint_index(crd))
		log.msg("Removing %s with value %s from ordered waypoints" % (str(owp[1]), owp[0]))
		self.sort_ordered()
		self.next_waypoint_index = self.waypoint_index(self.next_waypoint)

	def sort_ordered(self):
		self.ordered_waypoints = sorted( self.ordered_waypoints, key=lambda s: s[0])
		log.msg("Signs %s " % self.ordered_waypoints)
			
	def get_next_waypoint(self):
		if len(self.ordered_waypoints) < 2:
			self.next_waypoint = None
			self.next_waypoint_index = None
			return self.next_waypoint
		if self.next_waypoint is None:
			self.next_waypoint = self.ordered_waypoints[0][1]
			self.next_waypoint_index = 0
		else:
			self.next_waypoint_index += 1
			if self.next_waypoint_index >= len(self.ordered_waypoints):
				self.next_waypoint_index = 0
			self.next_waypoint = self.ordered_waypoints[self.next_waypoint_index][1]
		return (self.next_waypoint[0], self.next_waypoint[1] - 1, self.next_waypoint[2])

