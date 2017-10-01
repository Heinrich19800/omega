MODULE_NAME = 'PlayerAnnouncer'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_announcer'

DEFAULT_CONFIG = {
    'join': False,
    'join_message': '%RANK% %NAME% joined the server',
    'periodic': False,
    'periodic_message': 'Currently online survivors: %PLAYERS%/%MAXPLAYERS%'
}


class PlayerAnnouncer(object):
    def __init__(self, worker):
        self.config = DEFAULT_CONFIG

        self.worker = worker

        self.fetch_config()

        self.register_callbacks()
        
    def fetch_config(self):
        config = self.worker.get_module_config(MODULE_CONFIG_ID)
        if config:
            self.config = config
        
    def register_callbacks(self):
        self.worker.register_callback('player', 'guid', self.player_computed)
        self.worker.scheduler.add_task(self.periodic_message, 30, 60*5)
        self.worker.register_callback('tool', 'module_update', self.config_update)
        
    def config_update(self, module):
        if module == MODULE_CONFIG_ID:
            self.fetch_config()
        
    def player_computed(self, player):
        if not self.config.get('join'):
            return
        
        msg = player.construct_message(self.config.get('join_message'))
        self.worker.server.say_all(msg)
        
    def periodic_message(self, *_):
        if not self.config.get('periodic'):
            return
        
        msg = self.worker.construct_message(self.config.get('periodic_message'))
        self.worker.server.say_all(msg)
        
        
def hook():
    return [MODULE_NAME, MODULE_AUTHOR, PlayerAnnouncer]
