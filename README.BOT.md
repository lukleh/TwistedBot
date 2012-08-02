Bot for Minecraft
=================
Client side artificial player for Minecraft written in Python. Runs on vanilla server. No modification on server/client side needed.


STATUS
------------
broken, fixing it...

protocol parsing only, bot stays idle in the world (does not even fall now)

rest of the modules unplugged and/or under development


Current status
--------------
- Movemets & pathfinding. Only solid blocks. No web.
- Cannot process fluids(water, lava).
- No mobs, no food, crafting, combat etc.
- Simple short/medium distance navigation (walking between signs - waypoint/number)
- Understands only full blocks (no half slabs, doors etc.)
- If you want to change the server, username etc. look for twistedbot/config.py
- Run it only against offline mode servers - no authentication implemented.
- Parsing network stream correctly. Builds the grid and metadata correctly. Not all values used yet.
- Use at your own risk, pre-alpha quality.


Possible commands
-----------------
write into Minecraft chat. If your name is as commander in config.py, the bot will try the following

- "rotate" starts to walk between waypoints (detail below)
- "look at me" just starts to stare at you and turn if you move
- "cancel" cancel ongoing command


Waypoint
--------
* make a sign, then write on it
* line 1: "waypoint"
* line 2: a number, can be float and negative if needed. it represents the order of the waypoints


