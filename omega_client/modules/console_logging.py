from time import time

MODULE_NAME = 'ConsoleLogging'
MODULE_AUTHOR = 'philippj'

class ConsoleLogger(object):
    def __init__(self, worker):
        self.players = {}
        self._worker = worker

        self._register_callbacks()
        
    def _register_callbacks(self):
        self._worker.register_callback('player', 'guid', self.player_connected)
        self._worker.register_callback('player', 'disconnect', self.player_disconnected)
        self._worker.register_callback('player', 'kick', self.player_kicked)
        self._worker.register_callback('player', 'chat', self.player_chat)
        
        self._worker.register_callback('tool', 'started', self.tool_started)
        self._worker.register_callback('tool', 'stopped', self.tool_stopped)
        self._worker.register_callback('tool', 'offline', self.tool_offline)
        self._worker.register_callback('tool', 'error', self.tool_error)
        
    @property
    def _id(self):
        if self._worker.server_name:
            return self._worker.server_name
            
        else:
            return self._worker.server_id
        
    def player_connected(self, player):
        print '{} - [+] ({}) player_connect | {} (Slot: {}) {}, IP: {} ({})'.format(self._id, time(), player.name, player.slot, player.guid, player.ip, player.country_name)
        
    def player_disconnected(self, player):
        print '{} - [-] ({}) player_disconnect | {} {}'.format(self._id, time(), player.name, player.guid)
        
    def player_kicked(self, kick_data):
        player = kick_data.get('player')
        print '{} - [!] ({}) player_kicked | {} {}, by: {}, for: {}'.format(self._id, time(), player.name, player.guid, kick_data.get('method'), kick_data.get('reason'))
        
    def player_chat(self, chat_data):
        player = chat_data.get('player')
        message = chat_data.get('message_data')
        print '{} - [*] ({}) player_chat | {} {}, to: {}, message: {}'.format(self._id, time(), player.name, player.guid, message.get('destination'), message.get('message'))

    def tool_started(self, *_):
        print '{} - [!!!] ({}) tool_started'.format(self._id, time())
        
    def tool_stopped(self, reason):
        print '{} - [!!!] ({}) tool_stopped | {}'.format(self._id, time(), reason)
        
    def tool_offline(self, *_):
        print '{} - [!!!] ({}) tool_offline'.format(self._id, time())
    
    def tool_error(self, error):
        print '{} - [!!!] ({}) tool_error | {}'.format(self._id, time(), error)


def hook():
    return [MODULE_NAME, MODULE_AUTHOR, ConsoleLogger]