import threading
import json
import time
import importlib
import os
import sys

from cexceptions import *
from rcon import BattleEyeRcon
from location import OmegaLocation
from player import OmegaPlayer

"""

Will be finished on release of the DayZ SA server files
"""

OFFLINE_MAX_DURATION    = 30

script_path = os.path.dirname(os.path.realpath(__file__))

MODULE_DIR = '{}/modules'.format(script_path)
sys.path.append(MODULE_DIR)

PLAYERLIST_FETCH_INTERVAL = 5
CONFIG_FETCH_INTERVAL = 60*5
POLLING_INTERVAL = 3

class OmegaWorker(threading.Thread):
    def __init__(self, server_id, client):
        threading.Thread.__init__(self)
        self.server_id = server_id
        self._client = client
        
        self._rcon       = None
        self._active     = True
        self._ready      = False
        self._running    = False
        self._offline_time = 0
        
        self._fetches    = {
            'playerlist': 0,
            'config': 0,
            'master_poll': 0
        }
        
        self.config = {}
        
        self.players = {}
        
        self._callbacks = {
            'player': {
                'connect': [],
                'disconnect': [],
                'guid': [],
                'chat': [],
                'kick': [],
                'ping_update': []
            },
            'tool': {
                'started': [],
                'stopped': [],
                'offline': [],
                'error': []
            }
        }
        
        self.hive = 'public'
        self.server_name = False
        self.max_players = -1
        
        self._modules = []
        
        try:
            self.load_config()
            
        except OmegaWorkerError as exception:
            self.stop(wait=True)
            self._client._worker_reinitiate(self.server_id, 'local_config_not_found')
            
        self._load_modules()
        self.start()


    def _load_modules(self):
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
            
    def get_module_config(self, module_config_id):
        if module_config_id not in self.config.get('modules'):
            return False
            
        else:
            return self.config.get('modules').get(module_config_id)
            
    def register_callback(self, endpoint, action, method_reference):
        if endpoint not in self._callbacks:
            raise OmegaWorkerError('Cant register callback for unknown endpoint "{}"'.format(endpoint))

        if action not in self._callbacks[endpoint]:
            raise OmegaWorkerError('Cant register callback for unknown action "{}.{}"'.format(endpoint, action))

        self._callbacks[endpoint][action].append(method_reference)

    def _trigger_callback(self, endpoint, action, data=None):
        for method in self._callbacks.get(endpoint).get(action):
            method(data) 
            
    def load_config(self):
        self._fetches['config'] = time.time()
        config = self._client.retrieve_config(self.server_id)
        if not config:
            path = '{}{}.omegaconf'.format(LOCAL_CONFIG_PATH, self.server_id)
            if os.path.isfile(path):
                with open(path) as file:    
                    config = json.load(file) 
            
            else:
                raise OmegaWorkerError(self.server_id, '{} could not be found (no cloud config provided)'.format(path))
                
        self.config = config
        if 'steam_info' in config:
            self.steam_info = config.get('steam_info')
            
            if self.steam_info:
                if 'privHive' in self.steam_info.get('restricted').get('gametype'):
                    self.hive = 'private'
                    
                self.server_name = self.steam_info.get('name')
                self.max_players = self.steam_info.get('max_players')
                
        
    def _initiate_rcon(self):
        self._rcon = BattleEyeRcon(self.config.get('host'), self.config.get('port'), self.config.get('password'))
        self._rcon.register_callback('connection', 'authenticated', self._rcon_authenticated)
        self._rcon.register_callback('connection', 'authentication_failed', self._rcon_authentication_failed)
        self._rcon.register_callback('event', 'player_connect', self._player_connected)
        self._rcon.register_callback('event', 'player_disconnect', self._player_disconnected)
        self._rcon.register_callback('event', 'player_guid', self._player_guid)
        self._rcon.register_callback('event', 'player_list', self._player_list)
        self._rcon.register_callback('event', 'player_chat', self._player_chat)
        self._rcon.register_callback('event', 'be_kick', self._player_kick)
        self._rcon.register_callback('error', 'critical', self._error_critical)
        self._rcon.register_callback('error', 'connection_refused', self._error_connection_refused)
        self._rcon.register_callback('error', 'connection_closed', self._error_connection_closed)
        
    def _error_critical(self, *_):
        self.stop(wait=True, timeout=5)
        self._client._worker_reinitiate(self.server_id, 'critical_error')
        
    def _error_connection_refused(self, *_):
        self._trigger_callback('tool', 'error', 'rcon_connection_refused')
        self.stop(wait=True, timeout=60, reason='rcon_connection_refused')
        self._client._worker_reinitiate(self.server_id, 'rcon_connection_refused')
        
    def _error_connection_closed(self, *_):
        self._trigger_callback('tool', 'error', 'rcon_connection_closed')
        self.stop(wait=True, timeout=60, reason='rcon_connection_closed')
        self._client._worker_reinitiate(self.server_id, 'rcon_connection_closed')
        
    def _start_rcon(self):
        self._client._server_started(self.server_id)
        self._offline_time = 0
        self._rcon.connect()
        self._rcon.login()
        try:
            self._rcon.start()
            
        except RuntimeError as e:
            self._initiate_rcon()
            self._rcon.connect()
            self._rcon.login()
        
    def _rcon_authenticated(self, *_):
        self._ready = True
        self._client._server_online(self.server_id)
        self._rcon.say_all('------- CFTools --------')
        self._trigger_callback('tool', 'started')
        
    def _rcon_authentication_failed(self, *_):
        self.stop(wait=True, reason='rcon_authentication_failed')
        self._client._worker_kill(self.server_id, 'rcon_authentication_failed')
        self._trigger_callback('tool', 'stopped', 'rcon_authentication_failed')
        
    def _player_connected(self, player_data):
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
        self._trigger_callback('player', 'connect', player_object)
        
    def _player_disconnected(self, player_data):
        player_data = {
            'slot': player_data[0],
            'name': player_data[1]
        }
        self._trigger_callback('player', 'disconnect', 
                                        self.players[player_data.get('slot')])
        del self.players[player_data.get('slot')]
        
    def _player_guid(self, player_data):
        player_data = {
            'guid': player_data[0],
            'slot': player_data[1],
            'name': player_data[2]
        }
        self.players[player_data.get('slot')].set_guid(player_data.get('guid'))
        self._trigger_callback('player', 'guid', 
                                        self.players[player_data.get('slot')])
                                        
    def _player_list(self, players):
        for player in players:
            if player.get('slot') not in self.players \
            or player.get('guid') != self.players[player.get('slot')].guid:
                self._player_connected(
                    (player.get('slot'), player.get('name'), player.get('ip'))
                )
                self._player_guid(
                    (player.get('guid'), player.get('slot'), player.get('name'))
                )
        
            else:
                if player.get('ping') != self.players[player.get('slot')].ping:
                    self.players[player.get('slot')].ping = player.get('ping')
                    self._trigger_callback('player', 'ping_update', 
                                        self.players[player.get('slot')])
    
    def _player_kick(self, kick_data):
        kick_data = {
            'player': self.guid_to_player(kick_data[0]),
            'method': kick_data[1],
            'reason': kick_data[2]
        }
        
        self._trigger_callback('player', 'kick', kick_data)
        del self.players[kick_data.get('player').slot]
    
    def _player_chat(self, chat_data):
        chat_data = {
            'destination': chat_data[0].lower(),
            'name': chat_data[1],
            'message': chat_data[2]
        }

        self._trigger_callback('player', 'chat', {
                'player': self.name_to_player(chat_data.get('name')), 
                'message_data': chat_data
        })

    def _update_player_online_state(self, state, omega_id, server='', ip=''):
        self._client.request('player', omega_id, 'state', {
            'state': state,
            'server': server,
            'last_ip': ip
        })
    
    def _update_player_history(self, omega_id, name, ip, playtime, kicked=False, kicked_reason=''):
        self._client.request('player', omega_id, 'history', {
            'name': name,
            'ip': ip,
            'playtime': playtime #TODO: unused, still need this?
        })

    def name_to_player(self, name):
        for slot, player in self.players.iteritems():
            if player.name == name:
                return player
                
        return None
        
    def omega_id_to_player(self, omega_id):
        for slot, player in self.players.iteritems():
            if player.omega_id == omega_id:
                return player
                
        return None
        
    def guid_to_player(self, guid):
        for slot, player in self.players.iteritems():
            if player.guid == guid:
                return player
                
        return None
        
    def find_player_by_name(self, name):
        results = []
        
        if len(name) < 3:
            return results
        
        for slot, player in self.players.iteritems():
            if name.lower() in player.name.lower():
                results.append(player)
                
        return results
    
    def run(self):
        if not self._active:
            return
        
        self._running = True
            
        self._initiate_rcon()
        self._start_rcon()
        
        #TODO: find nicer way to poll
        _polling_thread = threading.Thread(target=self._polling)
        _polling_thread.start()
        while self._active:
            time.sleep(1)
            if int(time.time()) - self._fetches.get('config') > CONFIG_FETCH_INTERVAL:
                self.load_config()
                
            if not self._ready:
                self._offline_time += 1

                if self._offline_time >= OFFLINE_MAX_DURATION:
                    self.reinitiate(wait=True, reason='no_response_from_server')

            else: #TODO: do smth here... (polling maybe?)
                pass
                            
        self._rcon.stop()
        self._running = False
        
    #NOTICE: unused
    def _polling(self):
        while self._active:
            response = self._client.request('server', self.server_id, 'poll', timeout=65)

            if response.get('success'):
                orders = response.get('data').get('orders')
                for order in orders:
                    self._process_order(order.get('action'), order.get('params'))
        
    def _process_order(self, action, params):
        if action == 'kick':
            player = self.omega_id_to_player(params.get('omega_id'))
            if player:
                player.kick(params.get('reason'))
                
        elif action == 'global_message':
            self._rcon.say_all(params.get('message'))
            
        elif action == 'stop':
            self._rcon.say_all('CFTools instance stopped.')
            self.stop(reason=params.get('reason'))
            self._client._worker_kill(self.server_id, params.get('reason'))
            
    """
    TODO: rewrite stopping/reinitiating
    """
    
    def stop(self, wait=False, timeout=0, reason='shutdown'):
        self._client._server_offline(self.server_id, reason)
        self._active = False
        if wait:
            while self._running:
                time.sleep(.1)
            time.sleep(timeout)
            
    def reinitiate(self, wait=False, timeout=30, reason='reinitiate'):
        def _wait(self, timeout, reason):
            while self._running:
                time.sleep(.1)
            time.sleep(timeout)
            self._client._worker_reinitiate(self.server_id, reason)
            
        self._client._server_offline(self.server_id, reason)
        self._active = False
        if wait:
            _wait_thread = threading.Thread(target=_wait, args=(self, timeout, reason,))
            _wait_thread.start()
        