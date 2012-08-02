Proxy for Minecraft
===================

- make sure you use PyPy
- if you are runnig server, proxy and client on the same machine, have quad core
- keep in mind that thanks to the encryption, proxy has to first decrypt and encrypt again. specially with big packets as chunk bulks there is a noticeable delay


Usage
-----
### run with defaults server: localhost:25565 proxy: localhost:25566
pypy proxy.py

when you close proxy, it prints packet statistics before exit

### flags
pypy proxy.py -h

### packet print out
look in twistedbot.proxy_processors.default for an example





