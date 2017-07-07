from time import time

MODULE_NAME = 'ConsoleLogging'
MODULE_AUTHOR = 'philippj'

class ConsoleLogger(object):
    _worker = None
    
    players = {}
    
    def __init__(self, worker):
        self._worker = worker

        self._register_callbacks()
        
    def _register_callbacks(self):
        self._worker.register_callback('player', 'guid', self.player_connected)
        self._worker.register_callback('player', 'disconnect', self.player_disconnected)
        self._worker.register_callback('player', 'kick', self.player_kicked)
        self._worker.register_callback('player', 'chat', self.player_chat)
        
    def player_connected(self, player):
        print '[+] ({}) player_connect | {} {}, IP: {} ({})'.format(time(), player.name, player.guid, player.ip, player.country_name)
        
    def player_disconnected(self, player):
        print '[-] ({}) player_disconnect | {} {}'.format(time(), player.name, player.guid)
        
    def player_kicked(self, kick_data):
        player = kick_data.get('player')
        print '[!] ({}) player_kicked | {} {}, by: {}, for: {}'.format(time(), player.name, player.guid, kick_data.get('method'), kick_data.get('reason'))
        
    def player_chat(self, chat_data):
        player = chat_data.get('player')
        message = chat_data.get('message_data')
        print '[*] ({}) player_chat | {} {}, to: {}, message: {}'.format(time(), player.name, player.guid, message.get('destination'), message.get('message'))


def hook():
    return [MODULE_NAME, MODULE_AUTHOR, ConsoleLogger]