
import twistedbot.logbot

from twistedbot.plugins.base import PluginEventHandlerBase


log = twistedbot.logbot.getlogger("CORE EVENT")


class ProtocolEvents(PluginEventHandlerBase):

    def on_connection_made(self):
        self.world.connected = True
        self.world.send_packet("handshake", {"protocol": self.world.config.PROTOCOL_VERSION,
                                             "username": self.world.config.USERNAME,
                                             "server_host": self.world.config.SERVER_HOST,
                                             "server_port": self.world.config.SERVER_PORT})

    def on_connection_lost(self):
        self.world.connected = False
        self.world.logged_in = False
        self.world.protocol = None
        self.world.bot.on_connection_lost()

    def on_ping(self, ping_id):
        self.world.send_packet("keep alive", {"pid": ping_id})

    def on_login(self, bot_eid, level_type, game_mode, dimension, difficulty, max_players):
        log.msg("Login data: eid:%s level type:%s, game_mode:%s, dimension:%s, difficulty:%s, max players:%s" %
                (bot_eid, level_type, game_mode, dimension, difficulty, max_players))
        self.world.bot.eid = bot_eid
        self.world.logged_in = True
        self.world.dimension_change(dimension)
        self.world.game_mode = game_mode
        self.world.difficulty = difficulty
        self.world.bot.behavior_tree.blackboard.setup()
        self.world.send_packet("locale view distance", {'locale': self.world.config.LOCALE,
                                                         'view_distance': self.world.config.VIEWDISTANCE,
                                                         'chat_flags': 0,
                                                         'difficulty': self.world.config.DIFFICULTY,
                                                         'show_cape': False})

    def on_chat(self, message):
        msg = self.world.chat.clean(message)
        commander, command = self.world.chat.parse_message(msg)
        if commander == self.world.config.COMMANDER:
            log.msg("in # %s" % msg)
            self.world.chat.process_command(commander, command)

    def on_time_update(self, timestamp, daytime):
        self.world.timestamp = timestamp
        self.world.daytime = daytime

    def on_spawn_position(self, x, y, z):
        log.msg("Spawn position: %s %s %s" % (x, y, z))
        self.world.spawn_position = (x, y, z)
        self.world.bot.spawn_point_received = True

    def on_health_update(self, health, food, food_saturation):
        if health <= 0:
            self.world.eventregister.on_death.fire()

    def on_respawn(self, game_mode, dimension, difficulty):
        log.msg("RESPAWN received")
        self.world.dimension_change(dimension)
        self.world.game_mode = game_mode
        self.world.difficulty = difficulty
        self.world.bot.location_received = False
        self.world.bot.spawn_point_received = False
        self.world.bot.i_am_dead = False

    def on_location(self, x, y, z, stance, grounded, yaw, pitch):
        log.msg("received Location X:%.2f Y:%.2f Z:%.2f stance:%.2f grounded:%s yaw:%.2f pitch:%.2f" %
                (x, y, z, stance, grounded, yaw, pitch))
        self.world.bot.new_location(x=x, y=y, z=z, stance=stance, grounded=grounded, yaw=yaw, pitch=pitch)
        self.world.bot.send_location(self.world.bot.bot_object)

    def on_held_item_change(self, active_slot):
        log.msg("active slot changed to %d" % active_slot)
        self.world.inventories.active_slot_change(active_slot)

    def on_spawn_player(self, eid, username, held_item, yaw, pitch, x, y, z):
        self.world.entities.new_player(eid=eid, username=username,
                                          held_item=held_item, yaw=yaw,
                                          pitch=pitch, x=x, y=y, z=z)

    def on_collect(self, collected_eid, collector_eid):
        self.world.inventories.collect_action(collected_eid=collected_eid, collector_eid=collector_eid)

    def on_spawn_objectvehicle(self, eid, etype, x, y, z, object_data, velocity):
        self.world.entities.new_objectvehicle(eid=eid, etype=etype, x=x, y=y, z=z, object_data=object_data, velocity=velocity)

    def on_spawn_mob(self, eid, etype, x, y, z, yaw, pitch, head_yaw,
                     velocity_x, velocity_y, velocity_z, metadata):
        self.world.entities.new_mob(eid=eid, etype=etype, x=x, y=y, z=z, yaw=yaw, pitch=pitch, head_yaw=head_yaw,
                                       velocity_x=velocity_x, velocity_y=velocity_y, velocity_z=velocity_z, metadata=metadata)

    def on_spawn_painting(self, eid, x, y, z, title):
        self.world.entities.new_painting(eid=eid, x=x, y=y, z=z, title=title)

    def on_spawn_experience_orb(self, eid, count, x, y, z):
        self.world.entities.new_experience_orb(eid=eid, count=count, x=x, y=y, z=z)

    def on_entity_velocity(self, eid, x, y, z):
        self.world.entities.velocity(eid=eid, x=x, y=y, z=z)

    def on_entity_destroy(self, eids):
        self.world.entities.destroy(eids=eids)

    def on_entity_move(self, eid, dx, dy, dz):
        self.world.entities.move(eid=eid, dx=dx, dy=dy, dz=dz)

    def on_entity_look(self, eid, yaw, pitch):
        self.world.entities.look(eid=eid, yaw=yaw, pitch=pitch)

    def on_entity_move_look(self, eid, dx, dy, dz, yaw, pitch):
        self.world.entities.move_look(eid=eid, dx=dx, dy=dy, dz=dz, yaw=yaw, pitch=pitch)

    def on_entity_teleport(self, eid, x, y, z, yaw, pitch):
        self.world.entities.teleport(eid=eid, x=x, y=y, z=z, yaw=yaw, pitch=pitch)

    def on_entity_head_look(self, eid, yaw):
        self.world.entities.head_look(eid=eid, yaw=yaw)

    def on_entity_status(self, eid, status):
        self.world.entities.status(eid=eid, status=status)

    def on_entity_attach(self, eid, vehicle_id):
        self.world.entities.attach(eid=eid, vehicle_id=vehicle_id)

    def on_entity_metadata(self, eid, metadata):
        self.world.entities.metadata(eid=eid, metadata=metadata)

    def on_update_experience(self, experience_bar, level, total_experience):
        #TODO relevant when we can enchant or use anvil
        pass

    def on_load_chunk(self, x, z, continuous, primary_bit, add_bit, data_array):
        self.world.grid.load_chunk(x=x, z=z, continuous=continuous, primary_bit=primary_bit, add_bit=add_bit, data_array=data_array)

    def on_multi_block_change(self, x, z, blocks):
        self.world.grid.multi_block_change(chunk_x=x, chunk_z=z, blocks=blocks)

    def on_block_change(self, x, y, z, block_id, block_meta):
        self.world.grid.block_change(x=x, y=y, z=z, btype=block_id, bmeta=block_meta)

    def on_load_bulk_chunk(self, metas, data_array, light_data):
        self.world.grid.load_bulk_chunk(metas=metas, data_array=data_array, light_data=light_data)

    def on_explosion(self, x, y, z, radius, records, player_motion_x, player_motion_y, player_motion_z):
        log.msg("Explosion at %f %f %f radius %f blocks affected %d" % (x, y, z, radius, len(records)))
        self.world.grid.on_explosion(x=x, y=y, z=z, records=records)

    def on_open_window(self, window_id, window_type, extra_slots):
        self.world.inventories.open_window(window_id=window_id, window_type=window_type, extra_slots=extra_slots)
        
    def on_close_window(self, window_id):
        self.world.inventories.close_window(window_id=window_id)

    def on_set_window_slot(self, window_id, slot_id, slotdata):
        self.world.inventories.set_slot(window_id=window_id, slot_id=slot_id, slotdata=slotdata)

    def on_set_inventory(self, window_id, slotdata_list):
        self.world.inventories.set_slots(window_id=window_id, slotdata_list=slotdata_list)

    def on_confirm_transaction(self, window_id, action_number, confirmed):
        self.world.inventories.confirm_transaction(window_id=c.window_id, action_number=c.action_number, confirmed=c.confirmed)

    def on_update_sign(self, x, y, z, line1, line2, line3, line4):
        self.world.sign_waypoints.update_sign(x=x, y=y, z=z, line1=line1, line2=line2, line3=line3, line4=line4)

    def on_update_stats(self, stat_id, count):
        self.world.stats.update(stat_id, count)

    def on_player_list_item(self, name, online, ping):
        if online:
            self.world.players[name] = ping
        else:
            try:
                del self.world.players[name]
            except KeyError:
                pass

    def on_encryption_key_response(self):
        pass

    def on_encryption_key_request(self, server_id, public_key, verify_token):
        if self.world.config.USE_ENCRYPTION:
            log.msg('USE_ENCRYPTION is True, doing encryption.')
        else:
            log.msg('USE_ENCRYPTION is False, skipping encryption.')

    def on_server_kick(self, message):
        log.msg("Server kicked me out with message: %s" % message)
        from twisted.internet import reactor
        reactor.stop()


plugin = ProtocolEvents
