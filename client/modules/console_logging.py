from datetime import datetime
from time import time

MODULE_NAME = 'ConsoleLogging'
MODULE_AUTHOR = 'philippj'

DEFAULT_SERVERNAME = 'default servername'


class ConsoleLogger(object):
    def __init__(self, worker):
        self.players = {}
        self.worker = worker

        self._register_callbacks()
        
    def _register_callbacks(self):
        self.worker.register_callback('player', 'guid', self.player_connected)
        self.worker.register_callback('player', 'disconnect', self.player_disconnected)
        self.worker.register_callback('player', 'kick', self.player_kicked)
        self.worker.register_callback('player', 'chat', self.player_chat)
        self.worker.register_callback('tool', 'started', self.tool_started)
        self.worker.register_callback('tool', 'stopped', self.tool_stopped)
        self.worker.register_callback('tool', 'offline', self.tool_offline)
        self.worker.register_callback('tool', 'halted', self.tool_halted)
        self.worker.register_callback('tool', 'error', self.tool_error)
        self.worker.register_callback('tool', 'config_update', self.tool_config_update)
        self.worker.register_callback('tool', 'module_update', self.tool_module_update)
        
    @property
    def _id(self):
        if self.worker.servername and self.worker.servername != DEFAULT_SERVERNAME:
            return self.worker.servername
            
        else:
            return self.worker.server_id
            
    @property
    def time(self):
        return datetime.now().strftime('%H:%M:%S %d.%m.%Y')
        
    def player_connected(self, player):
        print '{} - [+] ({}) player_connect | {} (Slot: {}) {}, IP: {} ({})'.format(self._id, self.time, player.name, player.slot, player.guid, player.ip, player.country_name)
        
    def player_disconnected(self, player):
        if player.guid:
            print '{} - [-] ({}) player_disconnect | {} {}'.format(self._id, self.time, player.name, player.guid)
        
        else:
            print '{} - [-] ({}) player_disconnect | {} - Not fully connected'.format(self._id, self.time, player.name)
        
    def player_kicked(self, kick_data):
        player = kick_data.get('player')
        print '{} - [!] ({}) player_kicked | {} {}, by: {}, for: {}'.format(self._id, self.time, player.name, player.guid, kick_data.get('method'), kick_data.get('reason'))
        
    def player_chat(self, chat_data):
        player = chat_data.get('player')
        message = chat_data.get('message_data')
        print '{} - [*] ({}) player_chat | {} {}, to: {}, message: {}'.format(self._id, self.time, player.name, player.guid, message.get('destination'), message.get('message'))

    def tool_started(self, *_):
        print '\033[94m{} - [!!!] ({}) tool_started\033[0m'.format(self._id, self.time)
        
    def tool_stopped(self, reason):
        print '\033[91m{} - [!!!] ({}) tool_stopped | {}\033[0m'.format(self._id, self.time, reason)
        
    def tool_offline(self, *_):
        print '\033[91m{} - [!!!] ({}) tool_offline\033[0m'.format(self._id, self.time)
    
    def tool_error(self, error):
        print '\033[91m{} - [!!!] ({}) tool_error | {}\033[0m'.format(self._id, self.time, error)

    def tool_halted(self, reason):
        print '\033[91m{} - [!!!] ({}) tool_halted | {}\033[0m'.format(self._id, self.time, reason)
        
    def tool_config_update(self, value):
        print '\033[36m{} - [!!] ({}) tool_config_update | {} \033[0m'.format(self._id, self.time, value)
        
    def tool_module_update(self, module):
        print '\033[36m{} - [!!] ({}) tool_module_update | {} \033[0m'.format(self._id, self.time, module)

def hook():
    return [MODULE_NAME, MODULE_AUTHOR, ConsoleLogger]
