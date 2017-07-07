from time import time
import threading

MODULE_NAME = 'PingCheck'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_pingcheck'

DEFAULT_CONFIG = {
    'max_warnings': 10,
    'warning_threshold_timeout': 10,
    'max_ping': 250,
    'instant_kick_ping': 1000,
    'impossible_ping': 2000
}

class PingCheck(object):
    config = DEFAULT_CONFIG
    _worker = None
    
    players = {}
    
    def __init__(self, worker):
        self._worker = worker
        
        config = self._worker.get_module_config(MODULE_CONFIG_ID)
        if config:
            self.config = config
            
        self._register_callbacks()
        
    def _register_callbacks(self):
        self._worker.register_callback('player', 'guid', self.player_connected)
        self._worker.register_callback('player', 'disconnect', self.player_disconnected)
        self._worker.register_callback('player', 'ping_update', self.ping_updated)
        
    def player_connected(self, player):
        if player.guid not in self.players:
            self.players[player.guid] = {
                'ping_warnings': 0,
                'warning_threshold_start': time()
            }
        
    def player_disconnected(self, player):
        if player.guid in self.players:
            del self.players[player.guid]
        
    def ping_updated(self, player):
        if player.ping > self.config.get('impossible_ping'):
            return
        
        if time() > (self.players[player.guid].get('warning_threshold_start') 
                            + self.config.get('warning_threshold_timeout')):
            self.players[player.guid]['warning_threshold_start'] = time()
            self.players[player.guid]['ping_warnings'] = 0
        
        if player.ping > self.config.get('instant_kick_ping'):
            player.kick('Your ping is to high! ({})'.format(player.ping))
                
        if player.ping > self.config.get('max_ping'):
            self.players[player.guid]['ping_warnings'] += 1
            player.say('Your ping is too high! You will be kicked if it stays above the limit.')
            
        if self.players[player.guid]['ping_warnings'] > self.config.get('max_warnings'):
            player.kick('Your ping is to high! ({}, {}/{} Warnings)'.format(player.ping, self.config.get('max_warnings'), self.config.get('max_warnings')))
        

def hook():
    return [MODULE_NAME, MODULE_AUTHOR, PingCheck]
