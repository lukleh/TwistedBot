
from collections import defaultdict


GENERAL_STATS = 1000
ACHIEVEMENTS = 5242880
BLOCK_MINED = 16777216
ITEM_USED = 16908288
ITEM_BREAKED = 16973824

groups = {
    GENERAL_STATS: "general",
    ACHIEVEMENTS: "achievements"
}


class Statistics(object):
    def __init__(self):
        self.stats = defaultdict(lambda: 0)
        self.groupnames = sorted(groups.keys(), reverse=True)

    def update(self, sid, count):
        self.stats[sid] += count

    def get_groupname(self, stat_id):
        for km in self.groupnames:
            if stat_id >= km:
                return groups[km]

    def get_description(self, stat_id):
        if stat_id >= ITEM_BREAKED:
            return
        elif stat_id >= ITEM_USED:
            return
        elif stat_id >= BLOCK_MINED:
            return
        elif stat_id >= ACHIEVEMENTS:
            return
        elif stat_id >= GENERAL_STATS:
            return
        else:
            return "UNKNOWN"

    def __str__(self):
        for k, v in self.stats:
            self.get_groupname(k)
            self.get_description(k)
