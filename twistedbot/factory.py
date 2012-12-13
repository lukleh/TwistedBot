
from collections import deque


from twisted.internet.protocol import ReconnectingClientFactory, Protocol
from twisted.internet import reactor

import config
import logbot
import proxy_processors.default
import utils
from packets import parse_packets, make_packet, packets_by_name, Container
from proxy_processors.default import process_packets as packet_printout


proxy_processors.default.ignore_packets = []
proxy_processors.default.filter_packets = []

log = logbot.getlogger("PROTOCOL")


class MineCraftProtocol(Protocol):
    def __init__(self, world):
        self.world = world
        self.world.protocol = self
        self.leftover = ""
        self.encryption_on = False
        self.packets = deque()

        self.router = {
            0: self.p_ping,
            1: self.p_login,
            3: self.p_chat,
            4: self.p_time,
            5: self.p_entity_equipment,
            6: self.p_spawn,
            8: self.p_health,
            9: self.p_respawn,
            13: self.p_location,
            17: self.p_use_bed,
            18: self.p_animate,
            20: self.p_player,
            21: self.p_dropped_item,
            22: self.p_collect,
            23: self.p_vehicle,
            24: self.p_mob,
            26: self.p_experience_orb,
            28: self.p_entity_velocity,
            29: self.p_entity_destroy,
            31: self.p_entity_move,
            32: self.p_entity_look,
            33: self.p_entity_move_look,
            34: self.p_entity_teleport,
            35: self.p_entity_head_look,
            38: self.p_entity_status,
            39: self.p_entity_attach,
            40: self.p_entity_metadata,
            43: self.p_levelup,
            51: self.p_chunk,
            52: self.p_multi_block_change,
            53: self.p_block_change,
            54: self.p_block_action,
            55: self.p_block_break_animation,
            56: self.p_bulk_chunk,
            60: self.p_explosion,
            61: self.p_sound,
            62: self.p_named_sound,
            70: self.p_state,
            71: self.p_thunderbolt,
            103: self.p_window_slot,
            104: self.p_inventory,
            130: self.p_sign,
            132: self.p_update_tile,
            200: self.p_stats,
            201: self.p_players,
            202: self.p_abilities,
            203: self.p_tab_complete,
            252: self.p_encryption_key_response,
            253: self.p_encryption_key_request,
            255: self.p_error,
        }

    def connectionMade(self):
        self.world.connection_made()
        log.msg("sending HANDSHAKE")
        self.send_packet("handshake", {"protocol": config.PROTOCOL_VERSION,
                                       "username": config.USERNAME,
                                       "server_host": config.SERVER_HOST,
                                       "server_port": config.SERVER_PORT})

    def connectionLost(self, reason):
        self.packets = deque()
        self.world.on_connection_lost()

    def sendData(self, bytestream):
        if self.encryption_on:
            bytestream = self.cipher.encrypt(bytestream)
        self.transport.write(bytestream)

    def dataReceived(self, bytestream):
        try:
            self.parse_stream(bytestream)
        except:
            logbot.exit_on_error()

    def parse_stream(self, bytestream):
        if self.encryption_on:
            bytestream = self.decipher.decrypt(bytestream)
        parsed_packets, self.leftover = parse_packets(
            self.leftover + bytestream)
        if config.DEBUG:
            packet_printout(
                "SERVER", parsed_packets, self.encryption_on, self.leftover)
        self.packets.extend(parsed_packets)
        self.packet_iter(self.packets)

    def send_packet(self, name, payload):
        #print 'sending', name, payload
        p = make_packet(name, payload)
        if config.DEBUG:
            packet_printout(
                "CLIENT", [(packets_by_name[name], Container(**payload))])
        self.sendData(p)

    def packet_iter(self, ipackets):
        while ipackets:
            packet = ipackets.popleft()
            self.process_packet(packet)
            self.world.status_diff.packets_in += 1

    def process_packet(self, packet):
        pid = packet[0]
        payload = packet[1]
        f = self.router.get(pid, None)
        if f is not None:
            f(payload)
        else:
            log.msg("Unknown packet %d" % pid)
            reactor.stop()

    def p_ping(self, c):
        pid = c.pid
        self.send_packet("keep alive", {"pid": pid})

    def p_login(self, c):
        log.msg("LOGIN DATA eid %s level type: %s, game_mode: %s, dimension: %s, difficulty: %s, max players: %s" %
                (c.eid, c.level_type, c.game_mode, c.dimension, c.difficulty, c.players))
        self.world.on_login(bot_eid=c.eid, game_mode=c.game_mode, dimension=c.dimension, difficulty=c.difficulty)
        utils.do_now(self.send_packet, "locale view distance", {'locale': 'en_GB',
                                                                'view_distance': 2,
                                                                'chat_flags': 0,
                                                                'difficulty': 0,
                                                                'show_cape': False})

    def p_chat(self, c):
        self.world.chat.on_chat_message(c.message)

    def p_time(self, c):
        self.world.game_state.on_time_update(timestamp=c.timestamp, daytime=c.daytime)

    def p_entity_equipment(self, c):
        pass

    def p_spawn(self, c):
        log.msg("SPAWN POSITION %s %s %s" % (c.x, c.y, c.z))
        self.world.on_spawn_position(c.x, c.y, c.z)

    def p_health(self, c):
        self.world.bot.on_health_update(c.hp, c.fp, c.saturation)

    def p_respawn(self, c):
        log.msg("RESPAWN received")
        self.world.on_respawn(game_mode=c.game_mode, dimension=c.dimension, difficulty=c.difficulty)

    def p_location(self, c):
        #print 'p_location', c
        log.msg("received LOCATION X:%f Y:%f Z:%f STANCE:%f GROUNDED:%s" %
                (c.position.x, c.position.y, c.position.z,
                 c.position.stance, c.grounded.grounded))
        c.position.y, c.position.stance = c.position.stance, c.position.y
        self.send_packet("player position&look", c)
        self.world.bot.on_new_location({"x": c.position.x,
                                        "y": c.position.y,
                                        "z": c.position.z,
                                        "stance": c.position.stance,
                                        "grounded": c.grounded.grounded,
                                        "yaw": c.orientation.yaw,
                                        "pitch": c.orientation.pitch})

    def p_use_bed(self, c):
        """
        if ever will use bed, then deal with it.
        possibly also if commander uses bed.
        """
        pass

    def p_animate(self, c):
        #TODO this is two way, client uses only value 1 (swing arm). Probably needed.
        pass

    def p_player(self, c):
        self.world.entities.on_new_player(eid=c.eid, username=c.username,
                                          held_item=c.item, yaw=c.yaw,
                                          pitch=c.pitch, x=c.x, y=c.y, z=c.z)

    def p_dropped_item(self, c):
        self.world.entities.on_new_dropped_item(eid=c.eid, slotdata=c.slotdata, x=c.x,
                                                y=c.y, z=c.z, yaw=c.yaw,
                                                pitch=c.pitch, roll=c.roll)

    def p_collect(self, c):
        """ can be safely ignored, for animation purposes only """
        pass

    def p_vehicle(self, c):
        vel = {"x": c.velocity.x,
               "y": c.velocity.y,
               "z": c.velocity.z} if c.object_data > 0 else None
        self.world.entities.on_new_vehicle(eid=c.eid, etype=c.type,
                                           x=c.x, y=c.y, z=c.z,
                                           object_data=c.object_data,
                                           velocity=vel)

    def p_mob(self, c):
        self.world.entities.on_new_mob(eid=c.eid, etype=c.type, x=c.x, y=c.y,
                                       z=c.z, yaw=c.yaw, pitch=c.pitch,
                                       head_yaw=c.head_yaw,
                                       velocity_x=c.velocity_x,
                                       velocity_y=c.velocity_y,
                                       velocity_z=c.velocity_z,
                                       metadata=c.metadata)

    def p_experience_orb(self, c):
        self.world.entities.on_new_experience_orb(
            eid=c.eid, count=c.count, x=c.x, y=c.y, z=c.z)

    def p_entity_velocity(self, c):
        self.world.entities.on_velocity(c.eid, c.dx, c.dy, c.dz)

    def p_entity_destroy(self, c):
        self.world.entities.on_destroy(c.eids)

    def p_entity_move(self, c):
        self.world.entities.on_move(c.eid, c.dx, c.dy, c.dz)

    def p_entity_look(self, c):
        self.world.entities.on_look(c.eid, c.yaw, c.pitch)

    def p_entity_move_look(self, c):
        self.world.entities.on_move_look(c.eid, c.dx, c.dy, c.dz, c.yaw, c.pitch)

    def p_entity_teleport(self, c):
        self.world.entities.on_teleport(c.eid, c.x, c.y, c.z, c.yaw, c.pitch)

    def p_entity_head_look(self, c):
        self.world.entities.on_head_look(c.eid, c.yaw)

    def p_entity_status(self, c):
        self.world.entities.on_status(c.eid, c.status)

    def p_entity_attach(self, c):
        self.world.entities.on_attach(c.eid, c.vid)

    def p_entity_metadata(self, c):
        self.world.entities.on_metadata(c.eid, c.metadata)

    def p_levelup(self, c):
        self.world.bot.on_update_experience(experience_bar=c.current, level=c.level, total_experience=c.total)

    def p_chunk(self, c):
        self.world.grid.on_load_chunk(c.x, c.z, c.continuous, c.primary_bitmap,
                                      c.add_bitmap, c.data.decode('zlib'))

    def p_multi_block_change(self, c):
        self.world.grid.on_multi_block_change(c.x, c.z, c.blocks)

    def p_block_change(self, c):
        self.world.grid.on_block_change(c.x, c.y, c.z, c.type, c.meta)

    def p_block_action(self, c):
        """
        implement if necessary according to http://wiki.vg/Block_Actions
        """
        pass

    def p_block_break_animation(self, c):
        """ no need for this now """
        pass

    def p_bulk_chunk(self, c):
        self.world.grid.on_load_bulk_chunk(c.meta, c.data.decode('zlib'))

    def p_explosion(self, c):
        self.world.grid.on_explosion(c.x, c.y, c.z, c.records)
        log.msg("Explosion at %f %f %f radius %f blocks affected %d" %
                (c.x, c.y, c.z, c.radius, c.count))

    def p_sound(self, c):
        pass

    def p_named_sound(self, c):
        pass

    def p_state(self, c):
        pass

    def p_thunderbolt(self, c):
        pass

    def p_window_slot(self, c):
        pass

    def p_inventory(self, c):
        pass

    def p_sign(self, c):
        self.world.sign_waypoints.on_new_sign(c.x, c.y, c.z, c.line1, c.line2, c.line3, c.line4)

    def p_update_tile(self, c):
        pass
        #log.msg('Tile entity %s' % str(c))

    def p_stats(self, c):
        self.world.stats.on_update(c.sid, c.count)

    def p_players(self, c):
        if c.online:
            self.world.players[c.name] = c.ping
        else:
            try:
                del self.world.players[c.name]
            except KeyError:
                pass

    def p_abilities(self, c):
        pass

    def p_tab_complete(self, c):
        pass

    def p_encryption_key_response(self, c):
        self.encryption_on = True
        self.send_packet("client statuses", {"status": 0})

    def p_encryption_key_request(self, c):
        if config.USE_ENCRYPTION:
            try:
                import encryption
                key16 = encryption.get_random_bytes()
                self.cipher = encryption.make_aes(key16, key16)
                self.decipher = encryption.make_aes(key16, key16)
                public_key = encryption.load_pubkey(c.public_key)
                enc_shared_sercet = encryption.encrypt(key16, public_key)
                enc_4bytes = encryption.encrypt(c.verify_token, public_key)
                self.send_packet(
                    "encryption key response",
                    {"shared_length": len(enc_shared_sercet),
                     "shared_secret": enc_shared_sercet,
                     "token_length": len(enc_4bytes),
                     "token_secret": enc_4bytes})
            except ImportError:
                log.msg('PyCrypto not installed, skipping encryption.')
                self.send_packet("client statuses", {"status": 0})
        else:
            log.msg('USE_ENCRYPTION is False, skipping encryption.')
            self.send_packet("client statuses", {"status": 0})

    def p_error(self, c):
        log.msg("Server kicked me out with message: %s" % c.message)
        reactor.stop()


class MineCraftFactory(ReconnectingClientFactory):
    def __init__(self, world):
        self.world = world
        self.maxDelay = config.CONNECTION_MAX_DELAY
        self.initialDelay = config.CONNECTION_INITIAL_DELAY
        self.delay = self.initialDelay
        self.keyboard_kill = False

    def startedConnecting(self, connector):
        log.msg('Started connecting...')

    def buildProtocol(self, addr):
        log.msg('Connected!')
        if self.delay > self.initialDelay:
            log.msg('Resetting reconnection delay')
            self.resetDelay()
        protocol = MineCraftProtocol(self.world)
        protocol.factory = self
        return protocol

    def clientConnectionLost(self, connector, unused_reason):
        if not self.keyboard_kill:
            log.msg('Connection lost, reason:', unused_reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionLost(self, connector, unused_reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg('Connection failed, reason:', reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
