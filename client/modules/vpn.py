MODULE_NAME = 'VPNCheck'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_vpncheck'

DEFAULT_CONFIG = {
    'active': False,
    'kick_message': '%NAME% you have been kicked for using a VPN!'
}


class VPNCheck(object):
    def __init__(self, worker):
        self.config = DEFAULT_CONFIG

        self.worker = worker

        config = self.worker.get_module_config(MODULE_CONFIG_ID)
        if config:
            self.config = config

        self.register_callbacks()
        
    def register_callbacks(self):
        self.worker.register_callback('player', 'guid', self.player_computed)
        
    def player_computed(self, player):
        if not self.config.get('active'):
            return
        
        if player.uses_vpn:
            if self.worker.hive == 'public':
                return self.worker.trigger_callback('tool', 'error', 'VPNCheck would kick player but hive Public')
                
            player.kick(self.config.get('kick_message'))
        

def hook():
    return [MODULE_NAME, MODULE_AUTHOR, VPNCheck]
