
import argparse

import syspath_fix

from twisted.internet import reactor

from twistedbot.factory import MineCraftFactory
from twistedbot.world import World
from twistedbot.botentity import Bot
import twistedbot.logbot as logbot
import twistedbot.config as config


def start():
	log = logbot.getlogger("TOP")
	
	parser = argparse.ArgumentParser(description='Bot arguments.')
	parser.add_argument('--serverhost', default=config.SERVER_HOST, dest='serverhost', help='MC server host')
	parser.add_argument('--serverport', type=int, default=config.SERVER_PORT, dest='serverport', help='MC server port')
	args = parser.parse_args()
	
	host = args.serverhost 
	port = args.serverport
	name = config.USERNAME
	commander_name = config.COMMANDER

	world = World(host, port)
	bot = Bot(world, name, commander_name)

	reactor.addSystemEventTrigger("before", "shutdown", world.shutdown)
	reactor.connectTCP(host, port, MineCraftFactory(bot))
	reactor.run()


if __name__ == '__main__':
	start()
