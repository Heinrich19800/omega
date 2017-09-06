from time import time

from api.cftools import CFToolsAPI

class ServerStates:
    OFFLINE = 0
    STOPPED = 1
    STARTING = 2
    STARTING_CYLCE = 3
    ACTIVE = 4

class OmegaAPI(CFToolsAPI):
    
    def __init__(self, identity, key, error_mode=0, refresh_auth=True, headers={}, host='cfbackend.de', protocol='https'):
        CFToolsAPI.__init__(self, identity, key, 'omega', error_mode, refresh_auth, headers, host, protocol)
        
    def client_start(self, client_id):
        response = self.app_request({}, 'client', client_id, 'start')
        return response
        
    def client_stop(self, client_id):
        self.app_request({}, 'client', client_id, 'stop')
        
    def client_poll(self, client_id):
        response = self.app_request({}, 'client', client_id, 'poll', stream=True)
        return response
        
    def server_state(self, server_id, state, reason=''):
        payload = {
            'state': state,
            'reason': reason
        }
        self.app_request(payload, 'server', server_id, 'state')
        
    def update_player_state(self, omega_id, state, **kwargs):
        payload = {
            'state': state,
        }
        payload.update(kwargs)
        self.app_request(payload, 'player', omega_id, 'state')
        
    def player_query(self, beguid, server_id, container):
        payload = {
            'server_id': server_id,
            'container': container
        }
        response = self.app_request(payload, 'player', beguid, 'search')
        return response
        
    def player_create(self, beguid, payload):
        response = self.app_request(payload, 'player', beguid, 'create')
        return response
        
    def player_chat(self, beguid, omega_id, name, message, destination, server_id):
        payload = {
            'player': {
                'omega_id': omega_id,
                'guid': beguid,
                'name': name
            },
            'message': message,
            'destination': destination,
            'server_id': server_id
        }
        self.app_request(payload, 'player', omega_id, 'chat')        
