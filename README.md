Bot/Proxy for Minecraft
=======================
- support for 1.3.1 protocol version 39
- running under PyPy
- you can try cPython, if you want.

Proxy
=====
- if you are runnig server, proxy and client on the same machine, have quad core
- keep in mind that thanks to the encryption, proxy has to first decrypt and encrypt again. there is a noticeable delay

Usage
-----
- to run with defaults, server localhost:25565 proxy listening on localhost:25566
- $ pypy proxy.py
- when you close proxy, it prints packet statistics before exit

### flags
pypy proxy.py -h

### to make your own filter
look in twistedbot.proxy_processors.default for an example

Bot
===
- Client side artificial player for Minecraft written in Python. 
- Runs on vanilla server. 
- No modification on server/client side needed.

Status
------
- falls down to solid block
- respawn after death

Requirements
------------
PyCrypto. Rest is included in "libs"


### Credits
To all cool people creating all the cool stuff this bot depends on

twistedbot/packets.py - comment at the top of the file

U have question? NOT like something? @lukleh or github
