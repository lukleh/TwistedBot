

import signal
import argparse

import syspath_fix
syspath_fix.update_sys_path()

from twisted.internet import reactor
from twisted.protocols import basic

from twistedbot.factory import MineCraftFactory
from twistedbot.world import World
import twistedbot.config as config
import twistedbot.logbot as logbot


log = logbot.getlogger("MAIN")


class ConsoleChat(basic.LineReceiver):
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
    parser.add_argument('--log2file',
                        action='store_true',
                        help='Save log data to file')
    args = parser.parse_args()
    try:
        if args.log2file:
            logbot.start_bot_filelog()
    except:
        logbot.exit_on_error(_why="Cannot open log file for writing")
        exit()
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
    mc_factory = MineCraftFactory(world)

    def customKeyboardInterruptHandler(signum, stackframe):
        log.msg("CTRL-C from user, exiting....")
        mc_factory.log_connection_lost = False
        reactor.callFromThread(reactor.stop)

    signal.signal(signal.SIGINT, customKeyboardInterruptHandler)
    reactor.addSystemEventTrigger("before", "shutdown", world.on_shutdown)
    reactor.connectTCP(host, port, mc_factory)
    reactor.run()


if __name__ == '__main__':
    start()
