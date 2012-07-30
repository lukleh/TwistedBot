

import syspath_fix

import argparse
import sys
from datetime import datetime

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint
from twisted.python import log

from twistedbot.packets import make_packet, parse_packets, packets
from twistedbot import encryption
from twistedbot import logbot


log = logbot.getlogger("PROXY")
	
		
class ProxyProtocol(Protocol):

	def dataReceived(self, bytestream):
		try:
			self.parser(bytestream)
		except:
			logbot.exit_on_error()
			
	def sendData(self, bytestream):
		if self.encryption_on:
			bytestream = self.cipher.encrypt(bytestream)
		self.transport.write(bytestream)

	def parse_encrypted_stream(self, bytestream):
		plaintext = self.decipher.decrypt(bytestream)
		self.opposite_proxy_side.protocol.sendData(plaintext)
		data = self.leftover + plaintext
		parsed_packets, self.leftover = parse_packets(data)
		processor.process_packets(self.mgsside, parsed_packets, encrypted=True, leftover=self.leftover)
			
	def start_encryption(self):
		self.encryption_on = True
		self.parser = self.parse_encrypted_stream
		self.log.msg("Starting encryption")
			

class ProxyServerProtocol(ProxyProtocol):

	def __init__(self, factory):
		self.factory = factory
		self.encryption_on = False
		self.parser = self.parse_stream
		self.leftover = ""
		self.mgsside = self.factory.mgsside
		self.log = self.factory.log
		self.opposite_proxy_side = self.factory.proxyclient
		
	def connectionMade(self):
		self.log.msg("Made connection to server")
		self.factory.proxyclient.protocol.dataReceived("")
		
	def connectionLost(self, reason):
		self.log.msg("Lost connection from server")
		self.factory.proxyclient.protocol.transport.loseConnection()

	def parse_stream(self, bytestream):
		data = self.leftover + bytestream
		parsed_packets, self.leftover = parse_packets(data)
		processor.process_packets(self.mgsside, parsed_packets, leftover=self.leftover)
		for p in parsed_packets:
			if p[0] == 253:
				self.on_encryption_key_request(p[1])
				self.factory.proxyclient.protocol.send_encryption_key_request(p[1])
			elif p[0] == 252:
				""" STEP 4: initiate encryption on both side. """
				self.factory.proxyclient.protocol.sendData(data)
				self.start_encryption()
				self.factory.proxyclient.protocol.start_encryption()
			elif p[0] == 254:
				self.factory.proxyclient.protocol.sendData(data)
			elif p[0] == 255:
				self.factory.proxyclient.protocol.sendData(data)
			else:
				log.msg("packet %d cannot be unencrypted" % p[0])
		
	def on_encryption_key_request(self, c):
		"""
		STEP 2.1: decode encryption request from the server, use it for the server side
		"""
		aes_key = encryption.get_random_bytes()
		self.cipher = encryption.make_aes(aes_key , aes_key )
		self.decipher = encryption.make_aes(aes_key , aes_key )
		public_key = encryption.load_pubkey(c.public_key)
		self.enc_shared_sercet =  encryption.encrypt(aes_key , public_key)
		self.enc_4bytes = encryption.encrypt(c.verify_token, public_key)
		
	def send_encryption_key_response(self):
		"""
		STEP 3.2: send the server our AES key
		"""
		data = make_packet("encryption key response", {"shared_length": len(self.enc_shared_sercet), 
													"shared_secret": self.enc_shared_sercet,
													"token_length" : len(self.enc_4bytes),
													"token_secret" : self.enc_4bytes})
		self.sendData(data)
		
	def send_handshake(self, c):
		"""
		STEP 1: alter the received handshake packet from client and send it to the server
		"""
		c.server_host = self.factory.proxyclient.host
		c.server_port = self.factory.proxyclient.port
		data = chr(2) + packets[2].build(c)
		self.sendData(data)
		
		
class ProxyServerFactory(Factory):

	def __init__(self, proxyclient):
		self.mgsside = "SERVER"
		self.log = logbot.getlogger(self.mgsside)
		self.proxyclient = proxyclient
		
	def buildProtocol(self, addr):
		self.protocol = ProxyServerProtocol(self)
		return self.protocol
		
	def startedConnecting(self, connector):
		self.log.msg('Started connecting to server')

	def clientConnectionLost(self, connector, unused_reason):
		self.log.msg('Server connection lost, reason: %s' % unused_reason.getErrorMessage())

	def clientConnectionFailed(self, connector, reason):
		self.log.msg('Server connection failed, reason: %s' % reason.getErrorMessage())

		
class ProxyClientProtocol(ProxyProtocol):

	def __init__(self, factory):
		self.factory = factory
		self.encryption_on = False
		self.parser = self.parse_stream
		self.leftover = ""
		self.mgsside = self.factory.mgsside
		self.log = self.factory.log
		self.proxyserver = ProxyServerFactory(self.factory)
		self.opposite_proxy_side = self.proxyserver

	def connectionMade(self):
		self.log.msg("Received connection from client")
		endpoint = TCP4ClientEndpoint(reactor, self.factory.host, self.factory.port)
		d = endpoint.connect(self.proxyserver)
		d.addErrback(logbot.exit_on_error, "Server network error")
		
	def connectionLost(self, reason):
		self.log.msg("Lost connection from client")
		if self.proxyserver.protocol:
			self.proxyserver.protocol.transport.loseConnection()
	
	def parse_stream(self, bytestream):
		if self.proxyserver.protocol is None:
			self.log.msg("Not having connection to server yet, postpone proxying")
			self.leftover += bytestream
			return
		data = self.leftover + bytestream
		parsed_packets, self.leftover = parse_packets(data)
		processor.process_packets(self.mgsside, parsed_packets, leftover=self.leftover)
		for p in parsed_packets:
			if p[0] == 252:
				self.on_encryption_key_responce(p[1])
				self.proxyserver.protocol.send_encryption_key_response()
			elif p[0] == 2:
				self.proxyserver.protocol.send_handshake(p[1])
			elif p[0] == 254:
				self.proxyserver.protocol.sendData(data)
			elif p[0] == 255:
				self.proxyserver.protocol.sendData(data)
			else:
				log.msg("packet %d cannot be unencrypted" % p[0])
		
	def on_encryption_key_responce(self, c):
		"""
		STEP 3.1: decrypt client AES key with our RSA key
		"""
		aeskey = encryption.decrypt(c.shared_secret, self.factory.rsakey)
		self.cipher = encryption.make_aes(aeskey, aeskey)
		self.decipher = encryption.make_aes(aeskey, aeskey)
		
	def send_encryption_key_request(self, c):
		"""
		STEP 2.2: substitute our own key for the client side
		"""
		pubkey = encryption.export_pubkey(self.factory.rsakey)
		c.public_key_length = len(pubkey)
		c.public_key = pubkey
		c.token_length = 4
		c.verify_token = encryption.get_random_bytes(c.token_length)
		self.sendData(chr(253) + packets[253].build(c))


class ProxyClientFactory(Factory):

	def __init__(self, host, port):
		self.mgsside = "CLIENT"
		self.log = logbot.getlogger(self.mgsside)
		self.host = host
		self.port = port
		self.log.msg("Generating RSA key pair")
		self.rsakey = encryption.gen_rsa_key()
		
	def buildProtocol(self, addr):
		self.protocol = ProxyClientProtocol(self)
		return self.protocol
		
	def startFactory(self):
		self.log.msg("Proxy ready")

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Proxy arguments.')
	parser.add_argument('--serverhost', 
						default='localhost', 
						dest='serverhost', 
						help='MC server host')
	parser.add_argument('--serverport', 
						type=int, 
						default=25565, 
						dest='serverport', 
						help='MC server port')
	parser.add_argument('--proxyport', 
						type=int, 
						default=25566, 
						dest='proxyport', 
						help='proxy port')
	parser.add_argument('--processor', 
						default='default', 
						dest='processor', 
						help='Processor for packets, to print, save, analyze...')
	args = parser.parse_args()

	try:
		_procmod = __import__('twistedbot.proxy_processors', globals(), locals(), [args.processor], -1)
		processor = getattr(_procmod, args.processor)
	except:
		logbot.exit_on_error(_why="Cannot import %s" % ('proxy_processors.' + args.processor,))
		exit()
	
	endpoint = TCP4ServerEndpoint(reactor, args.proxyport)
	d = endpoint.listen(ProxyClientFactory(args.serverhost, args.serverport))
	d.addErrback(logbot.exit_on_error, "Client network error")
	reactor.addSystemEventTrigger('after', 'shutdown', processor.finish)
	reactor.run()
