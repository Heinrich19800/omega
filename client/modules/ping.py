MODULE_NAME = 'PingCheck'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_pingcheck'

DEFAULT_CONFIG = {
    'active': False,
    'max_warnings': 10,
    'max_ping': 250,
    'instant_kick_ping': 2000,
    'impossible_ping': 3000
}


class PingCheck(object):
    def __init__(self, worker):
        self.config = DEFAULT_CONFIG
        self.players = {}
        self.worker = worker

        self.fetch_config()

        self.register_callbacks()
        
    def fetch_config(self):
        config = self.worker.get_module_config(MODULE_CONFIG_ID)
        if config:
            self.config = config
        
    def register_callbacks(self):
        self.worker.register_callback('player', 'guid', self.player_computed)
        self.worker.register_callback('player', 'disconnect', self.player_disconnected)
        self.worker.register_callback('player', 'ping_update', self.ping_updated)
        self.worker.register_callback('tool', 'module_update', self.config_update)
        
    def config_update(self, module):
        if module == MODULE_CONFIG_ID:
            self.fetch_config()
        
    def player_computed(self, player):
        if player.guid not in self.players:
            self.players[player.guid] = {
                'ping_warnings': 0
            }
        
    def player_disconnected(self, player):
        if player.guid in self.players:
            del self.players[player.guid]
        
    def ping_updated(self, player):
        if not self.config.get('active'):
            return

        if player.ping >= self.config.get('impossible_ping'):
            return

        if player.ping >= self.config.get('instant_kick_ping'):
            player.kick('Your ping is to high! (%PING%)')
                
        if player.ping >= self.config.get('max_ping'):
            self.players[player.guid]['ping_warnings'] += 1
            player.say('Your ping is too high! You will be kicked if it stays above the limit.')
            
        if self.players[player.guid]['ping_warnings'] >= self.config.get('max_warnings'):
            player.kick('Your ping is to high! (%PING%, {}/{} Warnings)'.format(self.players[player.guid]['ping_warnings'], self.config.get('max_warnings')))
        

def hook():
    return [MODULE_NAME, MODULE_AUTHOR, PingCheck]
