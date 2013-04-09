
from collections import deque


from twisted.internet.protocol import ReconnectingClientFactory, Protocol
from twisted.internet import reactor
from twisted.web.client import getPage
from twisted.internet.defer import inlineCallbacks

import config
import hashlib
import logbot
import proxy_processors.default
import utils
from packets import parse_packets, make_packet, packets_by_name, Container
from proxy_processors.default import process_packets as packet_printout

encryption = None


def import_encryption():
    global encryption
    try:
        import encryption
    except ImportError:
        log.err('Encryption is demanded but PyCrypto not installed. This is not going to have a good end.')


proxy_processors.default.ignore_packets = []
proxy_processors.default.filter_packets = []

log = logbot.getlogger("PROTOCOL")


class MineCraftProtocol(Protocol):
    def __init__(self, world):
        self.world = world
        self.world.protocol = self
        self.event = world.eventregister
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
            16: self.p_held_item_change,
            17: self.p_use_bed,
            18: self.p_animate,
            20: self.p_spawn_player,
            22: self.p_collect,
            23: self.p_spawn_objectvehicle,
            24: self.p_spawn_mob,
            25: self.p_spawn_painting,
            26: self.p_spawn_experience_orb,
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
            41: self.p_entity_effect,
            42: self.p_entity_remove_effect,
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
            63: self.p_particle,
            70: self.p_state,
            71: self.p_thunderbolt,
            100: self.p_open_window,
            101: self.p_close_window,
            103: self.p_window_slot,
            104: self.p_inventory,
            105: self.p_update_window_property,
            106: self.p_confirm_transaction,
            130: self.p_sign,
            131: self.p_item_data,
            132: self.p_entity_update_tile,
            200: self.p_stats,
            201: self.p_players,
            202: self.p_abilities,
            203: self.p_tab_complete,
            206: self.p_create_scoreboard,
            207: self.p_update_scoreboard,
            208: self.p_display_scoreboard,
            208: self.p_teams,
            250: self.p_plugin_message,
            252: self.p_encryption_key_response,
            253: self.p_encryption_key_request,
            255: self.p_error,
        }

    def connectionMade(self):
        self.event.on_connection_made.fire()

    def connectionLost(self, reason):
        self.packets = deque()
        self.event.on_connection_lost.fire()

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
        parsed_packets, self.leftover = parse_packets(self.leftover + bytestream)
        if config.DEBUG:
            packet_printout("SERVER", parsed_packets, self.encryption_on, self.leftover)
        self.packets.extend(parsed_packets)
        self.packet_iter(self.packets)

    def send_packet(self, name, payload):
        p = make_packet(name, payload)
        if config.DEBUG:
            packet_printout("CLIENT", [(packets_by_name[name], Container(**payload))])
        self.sendData(p)

    def packet_iter(self, ipackets):
        while ipackets:
            packet = ipackets.popleft()
            self.process_packet(packet)

    def process_packet(self, packet):
        pid = packet[0]
        payload = packet[1]
        f = self.router.get(pid, None)
        if f is not None:
            #log.msg("packet %s %s" % (pid, f.__name__))
            f(payload)
        else:
            log.msg("Unknown packet %d" % pid)
            reactor.stop()

    def p_ping(self, c):
        self.event.on_ping.fire(ping_id=c.pid)

    def p_login(self, c):
        self.event.on_login.fire(bot_eid=c.eid, level_type=c.level_type, game_mode=c.game_mode, dimension=c.dimension, difficulty=c.difficulty, max_players=c.players)

    def p_chat(self, c):
        self.event.on_chat.fire(message=c.message)

    def p_time(self, c):
        self.event.on_time_update.fire(timestamp=c.timestamp, daytime=c.daytime)

    def p_entity_equipment(self, c):
        """ named entity eq, 0=held, 1-4=armor """
        pass

    def p_spawn(self, c):
        self.event.on_spawn_position.fire(x=c.x, y=c.y, z=c.z)

    def p_health(self, c):
        self.event.on_health_update.fire(health=c.hp, food=c.fp, food_saturation=c.saturation)

    def p_respawn(self, c):
        self.event.on_respawn.fire(game_mode=c.game_mode, dimension=c.dimension, difficulty=c.difficulty)

    def p_location(self, c):
        self.event.on_location.fire(x=c.position.x,
                                    y=c.position.stance,
                                    z=c.position.z,
                                    stance=c.position.y,
                                    grounded=c.grounded.grounded, 
                                    yaw=c.orientation.yaw,
                                    pitch=c.orientation.pitch)

    def p_held_item_change(self, c):
        self.event.on_held_item_change.fire(active_slot=c.active_slot)

    def p_use_bed(self, c):
        """
        if ever will use bed, then deal with it.
        possibly also if commander uses bed.
        """
        pass

    def p_animate(self, c):
        #TODO this is two way, client uses only value 1 (swing arm). Probably needed.
        pass

    def p_spawn_player(self, c):
        self.event.on_spawn_player.fire(eid=c.eid, username=c.username,
                                        held_item=c.item, yaw=c.yaw,
                                        pitch=c.pitch, x=c.x, y=c.y, z=c.z)

    def p_collect(self, c):
        self.event.on_collect.fire(collected_eid=c.collected_eid, collector_eid=c.collector_eid)

    def p_spawn_objectvehicle(self, c):
        vel = {"x": c.velocity.x,
               "y": c.velocity.y,
               "z": c.velocity.z} if c.object_data > 0 else None
        self.event.on_spawn_objectvehicle.fire(eid=c.eid, etype=c.type,
                                               x=c.x, y=c.y, z=c.z,
                                               object_data=c.object_data,
                                               velocity=vel)

    def p_spawn_mob(self, c):
        self.event.on_spawn_mob.fire(eid=c.eid, etype=c.type, x=c.x, y=c.y,
                                     z=c.z, yaw=c.yaw, pitch=c.pitch,
                                     head_yaw=c.head_yaw,
                                     velocity_x=c.velocity_x,
                                     velocity_y=c.velocity_y,
                                     velocity_z=c.velocity_z,
                                     metadata=c.metadata)

    def p_spawn_painting(self, c):
        self.event.on_spawn_painting.fire(eid=c.eid, x=c.x, y=c.y, z=c.z, title=c.title)

    def p_spawn_experience_orb(self, c):
        self.event.on_spawn_experience_orb.fire(eid=c.eid, count=c.count, x=c.x, y=c.y, z=c.z)

    def p_entity_velocity(self, c):
        self.event.on_entity_velocity.fire(eid=c.eid, x=c.x, y=c.y, z=c.z)

    def p_entity_destroy(self, c):
        self.event.on_entity_destroy.fire(eids=c.eids)

    def p_entity_move(self, c):
        self.event.on_entity_move.fire(eid=c.eid, dx=c.dx, dy=c.dy, dz=c.dz)

    def p_entity_look(self, c):
        self.event.on_entity_look.fire(eid=c.eid, yaw=c.yaw, pitch=c.pitch)

    def p_entity_move_look(self, c):
        self.event.on_entity_move_look.fire(eid=c.eid, dx=c.dx, dy=c.dy, dz=c.dz, yaw=c.yaw, pitch=c.pitch)

    def p_entity_teleport(self, c):
        self.event.on_entity_teleport.fire(eid=c.eid, x=c.x, y=c.y, z=c.z, yaw=c.yaw, pitch=c.pitch)

    def p_entity_head_look(self, c):
        self.event.on_entity_head_look.fire(eid=c.eid, yaw=c.yaw)

    def p_entity_status(self, c):
        self.event.on_entity_status.fire(eid=c.eid, status=c.status)

    def p_entity_attach(self, c):
        self.event.on_entity_attach.fire(eid=c.eid, vehicle_id=c.vehicle_id)

    def p_entity_metadata(self, c):
        self.event.on_entity_metadata.fire(eid=c.eid, metadata=c.metadata)

    def p_entity_effect(self, c):
        #TODO pass for now
        pass

    def p_entity_remove_effect(self, c):
        #TODO pass for now
        pass

    def p_levelup(self, c):
        self.event.on_update_experience.fire(experience_bar=c.current, level=c.level, total_experience=c.total)

    def p_chunk(self, c):
        self.event.on_load_chunk.fire(x=c.x, z=c.z, continuous=c.continuous, primary_bit=c.primary_bitmap,
                                      add_bit=c.add_bitmap, data_array=c.data.decode('zlib'))

    def p_multi_block_change(self, c):
        self.event.on_multi_block_change.fire(x=c.x, z=c.z, blocks=c.blocks)

    def p_block_change(self, c):
        self.event.on_block_change.fire(x=c.x, y=c.y, z=c.z, block_id=c.type, block_meta=c.meta)

    def p_block_action(self, c):
        """
        implement if necessary according to http://wiki.vg/Block_Actions
        """
        pass

    def p_block_break_animation(self, c):
        """ no need for this now """
        pass

    def p_bulk_chunk(self, c):
        self.event.on_load_bulk_chunk.fire(metas=c.meta, data_array=c.data.decode('zlib'), light_data=c.light_data)

    def p_explosion(self, c):
        self.event.on_explosion.fire(x=c.x, y=c.y, z=c.z, radius=c.radius, records=c.records, player_motion_x=c.player_motion_x,  player_motion_y=c.player_motion_y, player_motion_z=c.player_motion_z) 

    def p_sound(self, c):
        pass

    def p_named_sound(self, c):
        pass

    def p_particle(self, c):
        pass

    def p_state(self, c):
        pass

    def p_thunderbolt(self, c):
        pass

    def p_open_window(self, c):
        self.event.on_open_window.fire(window_id=c.window_id, window_type=c.window_type, extra_slots=c.extra_slots)

    def p_close_window(self, c):
        self.event.on_close_window.fire(window_id=c.window_id)

    def p_window_slot(self, c):
        self.event.on_set_window_slot.fire(window_id=c.window_id, slot_id=c.slot, slotdata=c.slotdata)

    def p_inventory(self, c):
        self.event.on_set_inventory.fire(window_id=c.window_id, slotdata_list=c.slotdata)

    def p_update_window_property(self, c):
        """ especially for furnace and enchantment table """
        pass

    def p_confirm_transaction(self, c):
        self.event.on_confirm_transaction.fire(window_id=c.window_id, action_number=c.action_number, confirmed=c.acknowledged)

    def p_sign(self, c):
        self.event.on_update_sign.fire(x=c.x, y=c.y, z=c.z, line1=c.line1, line2=c.line2, line3=c.line3, line4=c.line4)

    def p_item_data(self, c):
        """ data for map item """
        pass

    def p_entity_update_tile(self, c):
        #TODO figure out for what entities this applies
        pass

    def p_stats(self, c):
        self.event.on_update_stats.fire(stat_id=c.sid, count=c.count)

    def p_players(self, c):
        self.event.on_player_list_item.fire(name=c.name, online=c.online, ping=c.ping)

    def p_abilities(self, c):
        # TODO ignore for now
        pass

    def p_tab_complete(self, c):
        # ignore
        pass

    def p_create_scoreboard(self, c):
        # ignore
        pass

    def p_update_scoreboard(self, c):
        # ignore
        pass

    def p_display_scoreboard(self, c):
        # ignore
        pass

    def p_teams(self, c):
        # ignore
        pass

    def p_plugin_message(self, c):
        # ignore
        pass

    def p_encryption_key_response(self, c):
        self.event.on_encryption_key_response.fire()
        self.encryption_on = True
        self.send_packet("client statuses", {"status": 0})

    @inlineCallbacks
    def do_auth(self, id, key):
        log.msg('doing online authentication')
        shaobj = hashlib.sha1()
        shaobj.update(id)
        shaobj.update(self.factory.client_key)
        shaobj.update(key)
        d = long(shaobj.hexdigest(), 16)
        if d >> 39 * 4 & 0x8:
            d = "-%x" % ((-d) & (2 ** (40 * 4) - 1))
        else:
            d = "%x" % d
        hashstr = d
        url = "http://session.minecraft.net/game/joinserver.jsp?user=%s&serverId=%s&sessionId=%s" % (config.USERNAME, hashstr, self.factory.session_id)
        response = yield getPage(url).addErrback(logbot.exit_on_error)
        log.msg("responce from http://session.minecraft.net: %s" % response)

    @inlineCallbacks
    def p_encryption_key_request(self, c):
        self.event.on_encryption_key_request.fire(server_id=c.server_id, public_key=c.public_key, verify_token=c.verify_token)
        if config.USE_ENCRYPTION:
            self.cipher = encryption.make_aes(self.factory.client_key, self.factory.client_key)
            self.decipher = encryption.make_aes(self.factory.client_key, self.factory.client_key)
            public_key = encryption.load_pubkey(c.public_key)
            enc_shared_sercet = encryption.encrypt(self.factory.client_key, public_key)
            enc_4bytes = encryption.encrypt(c.verify_token, public_key)
            if config.ONLINE_LOGIN:
                yield self.do_auth(c.server_id, c.public_key)
            self.send_packet("encryption key response",
                             {"shared_length": len(enc_shared_sercet),
                             "shared_secret": enc_shared_sercet,
                             "token_length": len(enc_4bytes),
                             "token_secret": enc_4bytes})
        else:
            self.send_packet("client statuses", {"status": 0})

    def p_error(self, c):
        self.event.on_server_kick.fire(message=c.message)


class MineCraftFactory(ReconnectingClientFactory):
    def __init__(self, world):
        self.world = world
        self.world.factory = self
        self.maxDelay = config.CONNECTION_MAX_DELAY
        self.initialDelay = config.CONNECTION_INITIAL_DELAY
        self.delay = self.initialDelay
        self.log_connection_lost = True
        self.client_key = None
        self.clean_to_connect = True

    def startFactory(self):
        if config.USE_ENCRYPTION:
            self.client_key = encryption.get_random_bytes()

    @inlineCallbacks
    def online_auth(self):
        log.msg('doing online login')
        url = "http://login.minecraft.net/?user=%s&password=%s&version=1337" % (config.EMAIL, config.PASSWORD)
        response = yield getPage(url).addErrback(logbot.exit_on_error)
        log.msg("responce from http://login.minecraft.net: %s" % response)
        if ":" not in response:  # TODO well this is blunt approach, should use code with http code check
            self.clean_to_connect = False
            log.msg("did not authenticate with mojang, quiting")
            reactor.stop()
        else:
            _, _, config.USERNAME, self.session_id, _ = response.split(':')
            utils.do_later(10, self.keep_alive)

    def keep_alive(self):
        log.msg('keep alive to https://login.minecraft.net')
        url = "https://login.minecraft.net/session?name=%s&session=%s" % (config.USERNAME, self.session_id)
        getPage(url)
        utils.do_later(config.KEEP_ALIVE_PERIOD, self.keep_alive)

    def startedConnecting(self, connector):
        log.msg('started connecting to %s:%d' % (connector.host, connector.port))

    def buildProtocol(self, addr):
        log.msg('connected to %s:%d' % (addr.host, addr.port))
        if self.delay > self.initialDelay:
            log.msg('Resetting reconnection delay')
            self.resetDelay()
        protocol = MineCraftProtocol(self.world)
        protocol.factory = self
        return protocol

    def clientConnectionLost(self, connector, unused_reason):
        if self.log_connection_lost:
            log.msg('Connection lost, reason:', unused_reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionLost(self, connector, unused_reason)

    def clientConnectionFailed(self, connector, reason):
        if self.log_connection_lost:
            log.msg('Connection failed, reason:', reason.getErrorMessage())
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
