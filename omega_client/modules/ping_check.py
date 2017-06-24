import time
import threading

PLUGIN_NAME = 'PingCheck'
PLUGIN_AUTHOR = 'philippj'

PING_VALUES = {
    'warning': 100,
    'kick': 200
}

class PingCheck(object):
    _worker = None
    
    def __init__(self, worker):
        self._worker = worker
        self._register_callbacks()
        
    def _register_callbacks(self):
        self._worker.register_callback('player', 'ping_update', self.ping_updated)
        
    def ping_updated(self, player):
        print 'ping_update for {}, new ping: {}'.format(player.name, player.ping)
        if player.ping > PING_VALUES.get('warning'):
            if player.ping > PING_VALUES.get('kick'):
                player.kick('Your ping is too high!')
                
            else:
                player.say('You will be kicked if your ping stays above the limit.')
        

def hook():
    return [PLUGIN_NAME, PLUGIN_AUTHOR, PingCheck]
