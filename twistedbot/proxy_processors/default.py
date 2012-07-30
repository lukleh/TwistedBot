
import operator
import types
import pprint
from datetime import datetime
from collections import defaultdict

import twistedbot.logbot as logbot
from twistedbot.packets import packets
from twistedbot.packets import Container, Metadata

from pynbt import NBTFile


log = logbot.getlogger("-")

#########################################################################################################
# ignore_packets = [0, 4, 11, 12, 13, 24, 28, 29, 30, 31, 32, 33, 34, 35, 62] #these bring a lot of noise
# 0 keep alive
# 4 time update
# 11 player position
# 12 player look
# 13 player position&look
# 24 spawn mob
# 28 entity velocity
# 29 desctoy entity
# 30 entity
# 31 entity relative move
# 32 entity look
# 33 entity look and relative move
# 34 entity teleport
# 35 entity head look
# 62 named sound effect
#########################################################################################################

ignore_packets = []
filter_packets = []

statistics = defaultdict(lambda: defaultdict(int))	


def format_packet(data, prefix="  ", depth=1):
	""" return formated string of the packet """
	prefixstr = prefix * depth
	if isinstance(data, NBTFile):
		return data.pretty(indent=depth, indent_str=prefix)
	if isinstance(data, Container) or isinstance(data, types.DictType):
		out = []
		for k, v in data.iteritems():
			if isinstance(v, Metadata):
				pr = str(v.value)
			elif isinstance(v, types.StringType):
				if len(v) < 20:
					pr = v
				else:
					pr = v[:20], "... string is %d bytes long" % len(v)
			elif isinstance(v, types.BooleanType) or isinstance(v, types.IntType):
				pr = str(v)
			elif isinstance(v, types.LongType) or isinstance(v, types.FloatType):
				pr = str(v)
			elif isinstance(v, types.UnicodeType):
				pr = v.encode('utf8')
			elif isinstance(v, Container):
				pr = "\n%s" % format_packet(v, depth=depth+1)
			elif isinstance(v, types.TupleType) or isinstance(v, types.ListType):
				pr = "array length %d, first element:\n%s" % (len(v), format_packet(v[0], depth=depth+1))
			elif isinstance(v, types.NoneType):
				pr = str(v)
			elif isinstance(v, types.DictType):
				pr = "\n%s" % format_packet(v, depth=depth+1)
			else:
				pr = str(v)
			out.append("%s%s: %s" % (prefixstr, k, pr))
		if len(out) == 0:
			return "%s%s" % (prefixstr, "no body")
		else:
			return "\n".join(out)
	else:
		return str(data)


def process_packets(streamtype, pcks, encrypted=False, leftover=None):
	""" main function to use """
	if not pcks: return
	for p in pcks:
		packet_id = p[0]
		packet_body = p[1]
		statistics[streamtype][packet_id] += 1
		if packet_id in ignore_packets: continue
		if filter_packets and packet_id not in filter_packets: continue
		log.msg("id %d %s\n%s" % (packet_id, packets[packet_id].name, format_packet(packet_body)), header=streamtype)


def finish():
	""" 
		this is called when the proxy is about to exit to the system
		put here anything usefull, like printing statistics :)
	"""
	log.msg("STATISTICS")
	combined = defaultdict(int)
	for ptype in statistics.keys():
		psum = 0
		log.msg(ptype)
		sorted_p = sorted(statistics[ptype].iteritems(), key=operator.itemgetter(1), reverse=True)
		for pid, pcount in sorted_p:
			log.msg("\tid:\t%d\tcount\t%d\t%s" % (pid, pcount, packets[pid].name))
			combined[pid] += pcount
			psum += pcount
		log.msg("TOTAL: %d packets" % psum)
	log.msg("COMBINED")
	sorted_p = sorted(combined.iteritems(), key=operator.itemgetter(1), reverse=True)
	psum = 0
	for pid, pcount in sorted_p:
		log.msg( "\tid:\t%d\tcount\t%d\t%s" % (pid, pcount, packets[pid].name))
		psum += pcount
	log.msg("TOTAL: %d packets" % psum)
	

	
