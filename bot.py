
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
	parser.add_argument('--serverhost', default=config.SERVER_HOST, dest='serverhost', help='Minecraft server host')
	parser.add_argument('--serverport', type=int, default=config.SERVER_PORT, dest='serverport', help='Minecraft server port')
	parser.add_argument('--botname', default=config.USERNAME, dest='botname', help='username that will be used by the bot')
	parser.add_argument('--commandername', default=config.COMMANDER, dest='commandername', help='your username that you use in Minecraft')
	args = parser.parse_args()
	
	config.USERNAME = args.botname
	config.COMMANDER = args.commandername
	host = args.serverhost 
	port = args.serverport

	world = World(host, port)
	bot = Bot(world, args.botname, args.commandername)

	reactor.addSystemEventTrigger("before", "shutdown", world.shutdown)
	reactor.connectTCP(host, port, MineCraftFactory(bot))
	reactor.run()


if __name__ == '__main__':
	start()
