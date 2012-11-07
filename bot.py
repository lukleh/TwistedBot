

import syspath_fix
syspath_fix.update_sys_path()

import argparse

from twisted.internet import reactor
from twisted.protocols import basic

from twistedbot.factory import MineCraftFactory
from twistedbot.world import World
import twistedbot.config as config
import twistedbot.logbot as logbot


class ConsoleChat(basic.LineReceiver):
    from os import linesep as delimiter

    def __init__(self, world):
        self.world = world
        
    def lineReceived(self, line):
        try:
            self.world.chat.process_command(line)
        except Exception as e:
            logbot.exit_on_error(e)


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
    world = World(host=host, port=port, commander_name=args.commandername, bot_name=args.botname)
    try:
        from twisted.internet import stdio
        stdio.StandardIO(ConsoleChat(world))
    except ImportError:
        pass
    reactor.addSystemEventTrigger("before", "shutdown", world.shutdown)
    reactor.connectTCP(host, port, MineCraftFactory(world))
    reactor.run()


if __name__ == '__main__':
    start()
