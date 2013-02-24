

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
    from os import linesep as delimiter

    def __init__(self, world):
        self.world = world

    def connectionMade(self):
        log.msg("terminal chat available")

    def lineReceived(self, line):
        try:
            self.world.chat.process_command_line(line)
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
    parser.add_argument('--botpass', default=config.PASSWORD,
                        dest='botpass',
                        help='password that will be used by the bot')
    parser.add_argument('--botemail', default=config.EMAIL,
                        dest='botemail',
                        help='email address that will be used by the bot')
    parser.add_argument('--commandername', default=config.COMMANDER,
                        dest='commandername',
                        help='your username that you use in Minecraft')
    parser.add_argument('--log2file',
                        action='store_true',
                        help='Save log data to file')
    args = parser.parse_args()
    if args.log2file:
        logbot.start_bot_filelog()
    config.USERNAME = args.botname
    config.PASSWORD = args.botpass
    config.EMAIL = args.botemail
    config.COMMANDER = args.commandername.lower()
    host = args.serverhost
    port = args.serverport
    world = World(host=host, port=port, commander_name=args.commandername, bot_name=args.botname)
    try:
        from twisted.internet import stdio
        stdio.StandardIO(ConsoleChat(world))
    except ImportError:
        log.msg("no terminal chat available")

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
