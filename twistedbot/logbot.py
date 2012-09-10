
import sys
from datetime import datetime

from twisted.internet import reactor
from twisted.python import log, util


def exit_on_error(_stuff=None, _why=None):
	log.err(_stuff=_stuff, _why=_why)
	if reactor.running:
		reactor.stop()
	exit()

class MinecraftLogObserver(object):
	
	def __init__(self, f):
		self.write = f.write
		self.flush = f.flush

	def formatTime(self, when):
		t = datetime.fromtimestamp(when)
		return t.strftime("%H:%M:%S.%f")

	def emit(self, eventDict):
		if "isError" in eventDict and eventDict["isError"] and "header" not in eventDict:
			eventDict["header"] = "-"
		if "header" not in eventDict:
			return
		text = log.textFromEventDict(eventDict)
		if text is None:
			return
		timeStr = self.formatTime(eventDict['time'])
		fmtDict = {'header': eventDict['header'], 'text': text.replace("\n", "\n\t")}
		msgStr = log._safeFormat("[%(header)s] %(text)s\n", fmtDict)
		util.untilConcludes(self.write, timeStr + " " + msgStr)
		util.untilConcludes(self.flush) 
		
		
class Logger(object):
	
	def __init__(self, name):
		self.name = name
		
	def msg(self, *args, **kwargs):
		if "header" not in kwargs:
			kwargs["header"] = self.name
		log.msg(*args, **kwargs)
		
	def err(self, *args, **kwargs):
		if "header" not in kwargs:
			kwargs["header"] = self.name
		log.err(*args, **kwargs)	
		

loggers = {}
def getlogger(name):
	if name not in loggers:
		loggers[name] = Logger(name)
	return loggers[name]
	

def start_filelog(filename=None):
	if filename is None:
		filename = "%s.proxy_log.txt" % datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
	f = open(filename, "w")
	log.addObserver(MinecraftLogObserver(f).emit)
	msg("Started logging to file %s" % filename)
		

log.startLoggingWithObserver(MinecraftLogObserver(sys.stdout).emit, setStdout=0)

default_logger = getlogger("-")
default_logger.msg("Start logging")
msg = default_logger.msg
err = default_logger.err
