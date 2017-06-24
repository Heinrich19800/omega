import time
import threading

PLUGIN_NAME = 'WelcomeMessage'
PLUGIN_AUTHOR = 'philippj'

DEFAULT_WELCOME_MESSAGE = 'Welcome {NAME}. You are connecting from {COUNTRY}'

class WelcomeMessage(threading.Thread):
    _worker = None
    
    _scheduled_messages = []
    
    def __init__(self, worker):
        threading.Thread.__init__(self)
        self._worker = worker
        self.setDaemon(True)
        self.start()
        
        self._register_callbacks()
        
    def _register_callbacks(self):
        self._worker.register_callback('player', 'guid', self.player_computed)
        
    def _replace_variables(self, message, player):
        message = message.replace('{NAME}', player.name)
        message = message.replace('{IP}',   player.ip)
        message = message.replace('{GUID}', player.guid)
        message = message.replace('{SLOT}', player.slot)
        message = message.replace('{COUNTRY}', player.country_name)
        return message
        
    def player_computed(self, player):
        self._scheduled_messages.append({
            'player': player,
            'duration': 2,
            'message': self._replace_variables(DEFAULT_WELCOME_MESSAGE, player)
        })
        
    def run(self):
        while self._worker._active:
            time.sleep(1)
            for index, message in enumerate(self._scheduled_messages):
                message['duration'] -= 1
                if message.get('duration') == 0:
                    message.get('player').say(message.get('message'))
                    
                    del self._scheduled_messages[index]
                    
                else:
                    self._scheduled_messages[index] = message
                
        
def hook():
    return [PLUGIN_NAME, PLUGIN_AUTHOR, WelcomeMessage]
