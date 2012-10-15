
import math

DEBUG = False

COMMANDER = "lukleh"

USERNAME = "twistedbot"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 25565

PROTOCOL_VERSION = 39 # minecraft version 1.3.2
CONNECTION_MAX_DELAY = 5
CONNECTION_INITIAL_DELAY = 0.1 

WORLD_HEIGHT             = 256
CHUNK_SIDE_LEN            = 16
PLAYER_HEIGHT           = 1.74
PLAYER_EYELEVEL         = 1.62
PLAYER_BODY_EXTEND      = 0.3
PLAYER_BODY_DIAMETER    = 0.6

MAX_JUMP_HEIGHT            = 1.25
MAX_STEP_HEIGHT            = 0.5
G                        = 27.0 # or 0.08 block/tick - drag 0.02 blk/tick (used as final multiply by 0.98)

BLOCK_FALL                = 0.08
DRAG                     = 0.98
SPEED_ON_GROUND            = 0.1
SPEED_IN_AIR            = 0.02
SPEED_JUMP               = 0.42
SPEED_LIQUID_JUMP        = 0.03999999910593033
SPEED_CLIMB                = 0.2

TIME_STEP                = 0.05

COST_CLIMB                = 1.1
COST_LADDER                = 0.21/0.15 # common speed on ground / max speed on ladder
COST_FALL                = 1.1
COST_DIRECT                = 1
COST_DIAGONAL            = math.sqrt(2) * COST_DIRECT
ASTAR_LIMIT                = 100 # roughly 50 blocks