

import syspath_fix
syspath_fix.update_sys_path()

import argparse

from twisted.internet import reactor
from twisted.internet import stdio
from twisted.protocols import basic

from twistedbot.factory import MineCraftFactory
from twistedbot.world import World
from twistedbot.botentity import Bot
import twistedbot.config as config


class ConsoleChat(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self, bot):
        self.bot = bot
        
    def lineReceived(self, line):
        self.bot.chat.process_command(line)


def start():

    parser = argparse.ArgumentParser(description='Bot arguments.')
    parser.add_argument('--serverhost', default=config.SERVER_HOST,
                        dest='serverhost', help='Minecraft server host')
    parser.add_argument('--serverport', type=int, default=config.SERVER_PORT,
                        dest='serverport', help='Minecraft server port')
    parser.add_argument('--botname', default=config.USERNAME,
                        dest='botname',
                        help='username that will be used by the bot')
    parser.add_argument('--commandername', default=config.COMMANDER,
                        dest='commandername',
                        help='your username that you use in Minecraft')
    args = parser.parse_args()

    config.USERNAME = args.botname
    config.COMMANDER = args.commandername
    host = args.serverhost
    port = args.serverport

    world = World(host, port)
    bot = Bot(world, args.botname, args.commandername)
    stdio.StandardIO(ConsoleChat(bot))

    reactor.addSystemEventTrigger("before", "shutdown", world.shutdown)
    reactor.connectTCP(host, port, MineCraftFactory(bot))
    reactor.run()


if __name__ == '__main__':
    start()
