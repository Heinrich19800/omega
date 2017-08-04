import time
import threading

MODULE_NAME = 'Messenger'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_messenger'

DEFAULT_CONFIG = {
    'active': True,
    'welcome_message': {
            'message': 'Welcome {NAME}. You are connecting from {COUNTRY}',
            'delay': 2,
            'empty_lines': 0
        },
    'scheduled_messages': [
            {
                'interval': 180,
                'message': 'This is a CFTools enabled server'
            }
    ]
}

class Messenger(threading.Thread):
    def __init__(self, worker):
        threading.Thread.__init__(self)
        
        self.config = DEFAULT_CONFIG
        self._scheduled_messages = []
        
        self._worker = worker
        self.setDaemon(True)
        
        config = self._worker.get_module_config(MODULE_CONFIG_ID)
        if config:
            self.config = config
            
        if not self.config.get('active'):
            return
        
        self.start()
            
        for message in self.config.get('scheduled_messages'):
            self._scheduled_messages.append({
                'static': True,
                'message': message.get('message'),
                'duration': message.get('interval'),
                'interval': message.get('interval')
            })
        
        self._register_callbacks()
        
    def _register_callbacks(self):
        self._worker.register_callback('player', 'guid', self.player_computed)
        
    def _replace_variables(self, message, player):
        try:
            message = message.replace('{NAME}', player.name)
            
        except:
            message = message.replace('{NAME}', player.fix_name(player.name)) 
            
        message = message.replace('{IP}',   player.ip)
        message = message.replace('{GUID}', player.guid)
        message = message.replace('{SLOT}', player.slot)
        message = message.replace('{COUNTRY}', player.country_name)
        return message
        
    def player_computed(self, player):
        for _ in range(self.config.get('welcome_message').get('empty_lines')):
            self._scheduled_messages.append({
                'player': player,
                'duration': self.config.get('welcome_message').get('delay'),
                'message': ''
            })
            
        self._scheduled_messages.append({
            'player': player,
            'duration': self.config.get('welcome_message').get('delay'),
            'message': self._replace_variables(
                self.config.get('welcome_message').get('message'), player)
        })
        
    def run(self):
        while self._worker._active:
            time.sleep(1)
            for index, message in enumerate(self._scheduled_messages):
                message['duration'] -= 1
                if message.get('duration') == 0:
                    if 'static' not in message:
                        message.get('player').say(message.get('message'))
                        del self._scheduled_messages[index]
                        
                    else:
                        self._worker._rcon.say_all(message.get('message'))
                        message['duration'] = message.get('interval')
                        self._scheduled_messages[index] = message
                    
                else:
                    self._scheduled_messages[index] = message
                
        
def hook():
    return [MODULE_NAME, MODULE_AUTHOR, Messenger]
