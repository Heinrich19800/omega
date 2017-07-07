from time import time

from location import OmegaLocation

class OmegaPlayer(object):
    slot    = ''
    name    = ''
    ip      = ''
    guid    = ''
    ping    = 0
    
    player_data = None
    omega_id = ''
    
    _kicked = False
    _kicked_reason = ''
    _location = False
    
    _session_start = 0
    _worker = None
    
    _ts     = None
    _steam  = None
    _twitch = None
    _discord = None
    
    def __init__(self, worker, slot, name, ip):
        self._worker = worker
        
        self.slot = slot
        self.name = name
        self._session_start = time()
        self._location = OmegaLocation(ip)
        self.ip = '.'.join(ip.split('.')[0:3]) #german law things...
        
    def __del__(self):
        playtime = time()-self._session_start
        if self.omega_id:
            self._worker._update_player_online_state(False, self.omega_id, '')
            self._worker._update_player_history(
                self.guid, 
                self.name, 
                self.ip, 
                playtime,
                self._kicked,
                self._kicked_reason
                )
            
    def __getattr__(self, key):
        if key not in self._location._location_data.keys():
            raise AttributeError('No attribute "%s" '.format(repr(key)))
        return self._location._location_data.get(key)
        
    def set_guid(self, guid):
        self.guid = guid
        self._retrieve_player_data()
        if self.omega_id:
            self._worker._update_player_online_state(True, self.omega_id, self._worker.server_id)
        
    def _retrieve_player_data(self):
        timestamp = int(time())
        player_data = {
            'be_guid': self.guid,
            'last_ip': self.ip,
            'names': [self.name],
            'last_seen': timestamp,
            'first_seen': timestamp,
            'history': [],
            'ts_guid': '',
            'steam_id': '',
            'discord_id': '',
            'twitch_id': '',
            'origin_client': self._worker._client.client_id,
            'bans': [],
            'globalban': {
                'status': False,
                'enforceable': True,
                'reason': '',
                'timestamp': 0,
                'authorized_by': 'Omega Administrator'
            },
            'reports': [],
            'admin_rights': [],
            'online': True,
            'active_server': self._worker.server_id
        }
        response = self._worker._client.request('player', self.guid, 'query')
        if not response.get('success'):
            if response.get('error_message') == 'unknown_player_id':
                response = self._worker._client.request('client', self._worker._client.client_id, 'create_player', player_data)
                self.player_data = player_data
                self.omega_id = response.get('data').get('omega_id')
                
            else:
                self.player_data = False
                self.omega_id = ''
            
        else:
            self.player_data = response.get('data').get('player')
            self.omega_id = self.player_data.get('omega_id')
        
    def kick(self, reason='You have been kicked from the server'):
        self._kicked = True
        self._kicked_reason = reason
        self._worker._rcon.kick_player(self.slot, reason)
        
    def say(self, message=''):
        self._worker._rcon.say_player(self.slot, message)
        
    def rcon_ban(self, reason, time=0):
        self._kicked = True
        self._kicked_reason = 'Ban ({}): {}'.format(time, reason)
        self._worker._rcon.rcon_ban_player(self.slot, reason, time)