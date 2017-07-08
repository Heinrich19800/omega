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
            #'bans': [], #deprecated
            'globalban': {
                'status': False,
                'enforceable': True,
                'reason': '',
                'timestamp': 0,
                'authorized_by': 'Omega Administrator'
            },
            'reports': [],
            #'admin_rights': [], #deprecated
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
            
        if self.omega_id:
            additional_data = self._worker._client.request('server', self._worker.server_id, 'player', {
                'omega_id': self.omega_id
            })
            self.permission_level = additional_data.get('admin_state').get('level') if additional_data.get('admin_state') else 'player'
            self.whitelisted = additional_data.get('whitelist_state') if additional_data.get('whitelist_state') else False
            if self.whitelisted:
                if self.whitelisted.get('expires') != -1:
                    if time() > self.whitelisted.get('expires'):
                        self.whitelisted = False
            
            self.banned = additional_data.get('banned_state') if additional_data.get('banned_state') else False
            if self.banned:
                if self.banned.get('expires') != -1:
                    if time() > self.banned.get('expires'):
                        self.whitelisted = False
                        
            if self._worker.config.get('whitelist_enabled') and not self.whitelisted:
                self.kick('You are not listed on this servers whitelist')
                
            if self.banned:
                self.kick('You are banned from this server! ({})'.format(self.banned.get('reason')))
                
            if self.player_data.get('globalban').get('status'):
                if self._worker.config.get('accept_globalbans'):
                    self.kick('CFTools Globalban ({})'.format(self.player_data.get('globalban').get('reason')))
                    
                elif self.player_data.get('globalban').get('enforceable'):
                    self.kick('[ENFORCED] CFTools Globalban ({})'.format(self.player_data.get('globalban').get('reason')))
                    
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