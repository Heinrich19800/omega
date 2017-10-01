import os
import sys
import threading
import importlib
import time
import re

from lib.rcon.server2 import DayZServer, RCON_REGEX_LIST, RCON_PLAYERLIST_REGEX_EXTRA
from lib.player import OmegaPlayer
from lib.callback import Callback
from lib.scheduler import Scheduler
from api.omega import ServerStates

script_path = os.path.dirname(os.path.realpath(__file__))
script_path = script_path.replace('/lib', '')

MODULE_DIR = '{}/modules'.format(script_path)
sys.path.append(MODULE_DIR)

DEFAULT_SERVERNAME = 'default servername'


class OmegaWorker(Callback):
    def __init__(self, server_id, server_data, client):
        self.server_id = server_id
        self.client = client
        
        self.server_os = 'w'
        self.gamemap = 'chernarus+'
        self.hive = 'public'
        self.servername = DEFAULT_SERVERNAME
        self.max_players = 1
        self.gametime = '0:00'
        self.time_acceleration = 0
        
        self._update(server_data)
        
        self.players = {}
        self.first_players_fetch = True
        
        self.create_callbacks('player', [
            'connect',
            'disconnect',
            'guid',
            'chat',
            'kick',
            'ping_update'
        ])
        
        self.create_callbacks('tool', [
            'started',
            'stopped',
            'halted',
            'error',
            'config_update',
            'module_update',
            'notice'
        ])
        
        self.client.api.server_state(self.server_id, ServerStates.STARTING)
        
        self.setup_rcon()
        
        self.scheduler = Scheduler()
        self.tasks_created = False
        self.checkalive_fails = 0
        self.reconnects = 0
        
        self.start()
        
        self._modules = []
        self.load_modules()
        
    def get_module_config(self, module_config_id):
        if module_config_id not in self.config.get('modules'):
            return False
            
        else:
            return self.config.get('modules').get(module_config_id)
    
    def load_modules(self):
        module_files = []
        
        for module in os.listdir(MODULE_DIR):

            if module == '__init__.py' or module[-3:] != '.py':
                continue
            
            module_files.append(module[:-3])
        
        for file in module_files:
            try:
                name, author, reference = importlib.import_module(file).hook()
            except Exception as e:
                print '[MODULE] Error importing module {} ({})'.format(file, e)
                continue
            
            module = {
                'name': name,
                'author': author,
                'reference': reference,
                'instance': reference(self)
            }
            self._modules.append(module)
            
    def _update(self, server_data):
        self.config = server_data.get('config')
        self.container = self.config.get('container')
        self.steam_data = server_data.get('steam')
        
        if self.steam_data:
            gametype_params = self.steam_data.get('restricted').get('gametype').split(',')
            
            self.hive = 'private' if 'privHive' in gametype_params else 'public'
            self.third_pp = False if 'no3rd' in gametype_params else True
            
            if self.hive == 'public':
                self.gametime = gametype_params[5]
                self.time_acceleration = int(float(gametype_params[4].replace('etm', '')))
                
            else:
                self.gametime = gametype_params[6]
                self.time_acceleration = int(float(gametype_params[5].replace('etm', '')))

            self.server_os = self.steam_data.get('restricted').get('os')
            self.gamemap = self.steam_data.get('restricted').get('map')

            self.servername = self.steam_data.get('name')
            self.max_players = int(self.steam_data.get('max_players'))
        
            
    def get_player_by_name(self, name):
        for slot, player in self.players.iteritems():
            if player.name == name:
                return player
                
        return None
        
    def find_player_by_name(self, name):
        players = []
        for slot, player in self.players.iteritems():
            if name in player.name:
                players.append(player)
                
        return players
        
    def get_player_by_omega_id(self, omega_id):
        for slot, player in self.players.iteritems():
            if player.omega_id == omega_id:
                return player
                
        return None
        
    def get_player_by_guid(self, guid):
        for slot, player in self.players.iteritems():
            if player.guid == guid:
                return player
                
        return None
        
    def search_player_by_name(self, name):
        results = []
        
        if len(name) < 3:
            return results
        
        for slot, player in self.players.iteritems():
            if name.lower() in player.name.lower():
                results.append(player)
                
        return results
        
    def construct_message(self, message):
        message = str(message)
        message = message.replace('%SERVERNAME%', self.servername)
        message = message.replace('%HIVE%', self.hive) 
        message = message.replace('%MAXPLAYERS%', str(self.max_players))
        message = message.replace('%PLAYERS%', str(len(self.players)))
        return message
        
    def setup_rcon(self):
        self.server = DayZServer(self.config.get('host'), self.config.get('port'), self.config.get('password'))
        self.server.register_callback('connection', 'authenticated', self._cb_rcon_authenticated)
        self.server.register_callback('connection', 'authentication_failed', self._cb_rcon_authenticated_failed)
        self.server.register_callback('connection', 'keepalive_acknowledged', self._cb_rcon_keepalive_acknowledged)
        self.server.register_callback('event', 'player_connect', self._cb_player_connected)
        self.server.register_callback('event', 'player_disconnect', self._cb_player_disconnected)
        self.server.register_callback('event', 'player_guid', self._cb_player_guid)
        self.server.register_callback('event', 'player_list', self._cb_player_list)
        self.server.register_callback('event', 'player_chat', self._cb_player_chat)
        self.server.register_callback('event', 'be_kick', self._cb_player_kick)
        self.server.register_callback('error', 'connection_refused', self._cb_error_connection_refused)
        self.server.register_callback('error', 'connection_closed', self._cb_error_connection_closed)
        self.server.register_callback('error', 'checkalive_failed', self._cb_error_checkalive_failed)
    
    def start(self):
        self.server.start()
    
    def halt(self, reason='halted'):
        self.scheduler.suspend()
        self.server.stop()
        self.client.api.server_state(self.server_id, ServerStates.STOPPED, reason)
        self.trigger_callback('tool', 'halted', reason)
        self.first_players_fetch = True
        for slot in dict(self.players):
            self.trigger_callback('player', 'disconnect', self.players[slot])
            del self.players[slot]
    
    def stop(self, reason='shutdown'):
        self.scheduler.suspend()
        self.server.stop()
        self.client.api.server_state(self.server_id, ServerStates.STOPPED, reason)
        self.trigger_callback('tool', 'stopped', reason)
        self.first_players_fetch = True
        for slot in dict(self.players):
            self.trigger_callback('player', 'disconnect', self.players[slot])
            del self.players[slot]
        
    def _cb_rcon_authenticated(self, *_):
        if not self.tasks_created:
            self.scheduler.add_task(self.server.keepalive, 0, 10)
            self.scheduler.add_task(self.server.request_playerlist, 30, 30)
            self.tasks_created = True
            
        else:
            self.scheduler.resume()
            
        self.client.api.server_state(self.server_id, ServerStates.ACTIVE)
        self.server.say_all('------- CFTools --------')
        self.server.say_all('Starting up on {}'.format(self.server_id))
        self.server.say_all('{} server, time: {} (acceleration: {}), max players: {}, map: {}'.format(
            'windows' if self.server_os == 'w' else 'linux',
            self.gametime,
            self.time_acceleration,
            self.max_players,
            self.gamemap
        ))
        self.server.say_all('------- CFTools --------')
        self.reconnects = 0
        self.trigger_callback('tool', 'started')
    
    def _cb_rcon_authenticated_failed(self, *_):
        self.stop('rcon_authentication_failed')
        self.client.kill_worker(self.server_id)
        
    def _cb_error_connection_refused(self, data):
        self.client.api.server_state(self.server_id, ServerStates.STOPPED, reason='rcon_connection_refused')
        self.client.kill_worker(self.server_id, 'rcon_connection_refused')
        
    def _cb_error_connection_closed(self, data):
        self.halt('rcon_connection_closed')
        self.reconnects += 1
        if self.reconnects == 5:
            return self.server.trigger_callback('error', 'connection_refused')
            
        self.start()
        
    def _cb_rcon_keepalive_acknowledged(self, *_):
        self.checkalive_fails = 0
        
    def _cb_error_checkalive_failed(self, *_):
        self.checkalive_fails += 1
        self.trigger_callback('tool', 'error', '_cb_error_checkalive_failed ({}/2)'.format(self.checkalive_fails))
        if self.checkalive_fails >= 2:
            self.checkalive_fails = 0
            self.server.trigger_callback('error', 'connection_closed')
        
    def _cb_player_connected(self, player_data):
        player_data = {
            'slot': player_data[0],
            'name': player_data[1],
            'ip': player_data[2]
        }
        player_object = OmegaPlayer(
            self,
            player_data.get('slot'),
            player_data.get('name'),
            player_data.get('ip')
       )
        self.players[player_data.get('slot')] = player_object
        self.trigger_callback('player', 'connect', player_object)
        
    def _cb_player_disconnected(self, player_data):
        player_data = {
            'slot': player_data[0],
            'name': player_data[1]
        }
        if player_data.get('slot') not in self.players:
            return
        
        self.trigger_callback('player', 'disconnect', self.players[player_data.get('slot')])
        del self.players[player_data.get('slot')]
        
    def _cb_player_guid(self, player_data):
        player_data = {
            'guid': player_data[0],
            'slot': player_data[1],
            'name': player_data[2]
        }
        if player_data.get('slot') not in self.players:
            return
        
        self.players[player_data.get('slot')].set_guid(player_data.get('guid'))
        
        if player_data.get('slot') in self.players:
            self.trigger_callback('player', 'guid', self.players[player_data.get('slot')])
        
    def _cb_player_list(self, raw_players):
        players = []
        raw_players = raw_players.split('\n')
        del raw_players[0:3]
        del raw_players[-1]
        
        for player in raw_players:
            lobby = True
            player_data = re.search(RCON_PLAYERLIST_REGEX_EXTRA.get('player_list_lobby'), player)
            
            if player_data == None:
                lobby = False
                player_data = re.search(RCON_PLAYERLIST_REGEX_EXTRA.get('player_list_ingame'), player)
                
            if player_data == None:
                continue
            
            else:
                player_data = player_data.groups()
                    
            try:
                players.append({
                    'slot': player_data[0],
                    'ip': player_data[1].split(':')[0],
                    'ping': int(player_data[2]),
                    'guid': player_data[3],
                    'name': player_data[4],
                    'lobby': lobby
                })
                
            except:
                continue
                        
        for player in players:
            if player.get('slot') not in self.players or player.get('guid') != self.players[player.get('slot')].guid:
                if self.first_players_fetch:
                    self._cb_player_connected(
                        (player.get('slot'), player.get('name'), player.get('ip'))
                    )
                    self._cb_player_guid(
                        (player.get('guid'), player.get('slot'), player.get('name'))
                    )
        
            else:
                if player.get('ping') != self.players[player.get('slot')].ping:
                    self.players[player.get('slot')].ping = player.get('ping')
                    self.trigger_callback('player', 'ping_update', self.players[player.get('slot')])
        
        self.first_players_fetch = False

    def _fake_kick_event(self, player): # Kick event for public hives, for printing reason
        kick_data = {
            'player': player,
            'reason': player.reason
        }

        self.trigger_callback('player', 'kick', kick_data)
        del self.players[kick_data.get('player').slot]

    def _cb_player_kick(self, kick_data):
        kick_data = {
            'player': self.get_player_by_guid(kick_data[0]),
            'reason': kick_data[1]
        }

        self.trigger_callback('player', 'kick', kick_data)
        del self.players[kick_data.get('player').slot]
    
    def _cb_player_chat(self, chat_data):
        chat_data = {
            'destination': chat_data[0].lower(),
            'name': chat_data[1],
            'message': chat_data[2]
        }
        player = self.get_player_by_name(chat_data.get('name'))
        
        self.client.api.player_chat(player.guid, player.omega_id, chat_data.get('name'), chat_data.get('message'), chat_data.get('destination'), self.server_id)
        
        self.trigger_callback('player', 'chat', {
            'player': player, 
            'message_data': chat_data
        })
