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

OFFLINE_MAX_DURATION    = 60

script_path = os.path.dirname(os.path.realpath(__file__))

MODULE_DIR = '{}/modules'.format(script_path)
sys.path.append(MODULE_DIR)

PLAYERLIST_FETCH_INTERVAL = 5

class OmegaWorker(threading.Thread):
    server_id   = ''
    _client     = None
    _rcon       = None
    _active     = True
    _ready      = False
    _running    = False
    _offline_time = 0
    
    _fetches    = {
        'playerlist': 0
    }
    
    config = {}
    
    players = {}
    
    _callbacks = {
        'player': {
            'connect': [],
            'disconnect': [],
            'guid': [],
            'chat': [],
            'ping_update': []
        }
    }
    
    _modules = []
    
    
    def __init__(self, server_id, client):
        threading.Thread.__init__(self)
        self.server_id = server_id
        self._client = client

        self._load_modules()      

        try:
            self.load_config()
            
        except OmegaWorkerError as exception:
            self.stop(wait=True)
            self._client._worker_reinitiate(self.server_id, 'local_config_not_found')
        
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
            print '[MODULE] {} by {} loaded'.format(module.get('name'), module.get('author'))
            
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
        config = self._client.retrieve_config(self.server_id)
        if not config:
            path = '{}{}.omegaconf'.format(LOCAL_CONFIG_PATH, self.server_id)
            if os.path.isfile(path):
                with open(path) as file:    
                    config = json.load(file) 
            
            else:
                raise OmegaWorkerError(self.server_id, '{} could not be found (no cloud config provided)'.format(path))
                
        self.config = config
        
    def _initiate_rcon(self):
        self._rcon = BattleEyeRcon(self.config.get('host'), self.config.get('port'), self.config.get('password'))
        self._rcon.register_callback('connection', 'authenticated', self._rcon_authenticated)
        self._rcon.register_callback('connection', 'authentication_failed', self._rcon_authentication_failed)
        self._rcon.register_callback('event', 'player_connect', self._player_connected)
        self._rcon.register_callback('event', 'player_disconnect', self._player_disconnected)
        self._rcon.register_callback('event', 'player_guid', self._player_guid)
        self._rcon.register_callback('event', 'player_list', self._player_list)
        self._rcon.register_callback('event', 'player_chat', self._player_chat)
        
    def _start_rcon(self):
        self._client._server_started(self.server_id)
        self._offline_time = 0
        self._rcon.connect()
        self._rcon.login()
        self._rcon.start()
        
    def _rcon_authenticated(self, *_):
        self._ready = True
        self._client._server_online(self.server_id)
        
    def _rcon_authentication_failed(self, *_):
        self.stop(wait=True)
        self._client._worker_reinitiate(self.server_id, 'rcon_authentication_failed')
        
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
    
    def _player_chat(self, chat_data):
        chat_data = {
            'destination': chat_data[0].lower(),
            'name': chat_data[1],
            'message': chat_data[2]
        }

        self._trigger_callback('player', 'chat', {
                'player': self.name_to_player(chat_data.get('name')), 
                'player': chat_data
        })

    def _update_player_online_state(self, state, omega_id, server=''):
        self._client.request('player', omega_id, 'state', {
            'state': state,
            'server': server
        })
    
    def _update_player_history(self, omega_id, name, ip, playtime, kicked=False, kicked_reason=''):
        pass

    def name_to_player(self, name):
        for slot, player in self.players.iteritems():
            if player.name == name:
                return player
                
        return None
    
    def run(self):
        if not self._active:
            return
        
        self._running = True
            
        self._initiate_rcon()
        self._start_rcon()
        while self._active:
            time.sleep(1)
            if not self._ready:
                self._offline_time += 1
                
                if self._offline_time > OFFLINE_MAX_DURATION:
                    self._start_rcon()
                    #self._client._server_offline(self.server_id)
            
            else: #fetching data periodically
                if int(time.time()) - self._fetches.get('playerlist') > PLAYERLIST_FETCH_INTERVAL:
                    self._rcon.command('players')
                
                    
        self._running = False
    
    def stop(self, wait=False):
        self._active = False
        if wait:
            while self._running:
                time.sleep(.1)