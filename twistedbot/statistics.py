
from collections import defaultdict


class Statistics(object):
	def __init__(self):
		self.stats = defaultdict(lambda: 0)

	def update(self, sid, count):
		self.stats[sid] += count
