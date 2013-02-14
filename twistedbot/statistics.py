
from collections import defaultdict

import logbot
import items
import blocks


log = logbot.getlogger("STATISTICS")

GENERAL_STATS = 1000
ACHIEVEMENTS = 5242880
BLOCK_MINED = 16777216
ITEM_CRAFTED = 16842752
ITEM_USED = 16908288
ITEM_BREAKED = 16973824

ACHIEVEMENT_NAMES = ["openInventory",
                     "mineWood",
                     "buildWorkBench",
                     "buildPickaxe",
                     "buildFurnace",
                     "acquireIron",
                     "buildHoe",
                     "makeBread",
                     "bakeCake",
                     "buildBetterPickaxe",
                     "cookFish",
                     "onARail",
                     "buildSword",
                     "killEnemy",
                     "killCow",
                     "flyPig"]

GENERAL_NAMES = {1000: "startGame",
                 1001: "createWorld",
                 1002: "loadWorld",
                 1003: "joinMultiplayer",
                 1004: "leaveGame",
                 1100: "playOneMinute",
                 2000: "walkOneCm",
                 2001: "swimOneCm",
                 2002: "fallOneCm",
                 2003: "climbOneCm",
                 2004: "flyOneCm",
                 2005: "diveOneCm",
                 2006: "minecartOneCm",
                 2007: "boatOneCm",
                 2008: "pigOneCm",
                 2010: "jump",
                 2011: "drop",
                 2020: "damageDealt",
                 2021: "damageTaken",
                 2022: "deaths",
                 2023: "mobKills",
                 2024: "playerKills",
                 2025: "fishCaught"}


class Statistics(object):
    def __init__(self):
        self.stats = defaultdict(lambda: 0)

    def on_update(self, sid, count):
        log.msg('update %d by %d' % (sid, count))
        self.stats[sid] += count

    def get_description(self, stat_id):
        if stat_id >= ITEM_BREAKED:
            item_id = stat_id - ITEM_BREAKED
            return "%s breaked" % items.item_list[item_id].name
        elif stat_id >= ITEM_USED:
            item_id = stat_id - ITEM_USED
            return "%s used" % items.item_list[item_id].name
        elif stat_id >= ITEM_CRAFTED:
            item_id = stat_id - ITEM_CRAFTED
            return "%s crafted" % items.item_list[item_id].name
        elif stat_id >= BLOCK_MINED:
            block_id = stat_id - BLOCK_MINED
            return "%s mined" % blocks.block_list[block_id].name
        elif stat_id >= ACHIEVEMENTS:
            return ACHIEVEMENT_NAMES[stat_id - ACHIEVEMENTS]
        elif stat_id >= GENERAL_STATS:
            return GENERAL_NAMES[stat_id - GENERAL_STATS]
        else:
            raise Exception("unknown statistics id %d" % stat_id)

    def __repr__(self):
        "\n".join(["%s %d" % (self.get_description(k), v) for k, v in self.stats])
