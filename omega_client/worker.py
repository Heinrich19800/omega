import json

from cexceptions import BattleEyeRconError
from rcon import BattleEyeRcon

"""

Will be finished when the DayZ SA server files are being released.
"""

class OmegaWorker(object):
    server_id = ''
    _client = None
    _rcon = None
    _active = True
    
    config = {}
    
    def __init__(self, server_id, client):
        self.server_id = server_id
        self._client = client
        self.load_config()
        self._rcon = BattleEyeRcon(self.config.get('host'), self.config.get('port'), self.config.get('password'))
        
    def load_config(self):
        config = self._client.retrieve_config(self.server_id)
        if config == None:
            path = '{}{}.omegaconf'.format(LOCAL_CONFIG_PATH, self.server_id)
            if os.path.isfile(path):
                with open(path) as file:    
                    config = json.load(file) 
            
            else:
                self._active = False
                raise OmegaWorkerError(self.server_id, '{} could not be found (no cloud config provided)'.format(path))
                
        self.config = config

    def run(self):
        pass
    
    def stop(self):
        self._active = False