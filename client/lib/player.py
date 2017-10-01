from time import time

FIRST_TIME_MESSAGES = """Hello %NAME%! This is your first visit on a CFTools enabled Server!
    CFTools enables server admins to better administrate their server.
    Whenever you play on any CFTools enabled server, some of your data will be saved.
    You can terminate your account at <omega.cftools.de>."""
    

class OmegaPlayer(object):
    def __init__(self, worker, slot, name, ip):
        self.guid    = ''
        self.ping    = 0
        self.kicked  = False
        self.reason = 'Disconnect'
        
        self.player_data = None
        self.omega_id = ''
        self.permission_level = 'player'
        
        self.steam = False
        self.steam_profile_state = 'public'
        self.dayz_playtime = -1
        
        self.worker = worker

        self.slot = slot
        self.name = u'{}'.format(name)
        self.session_start = time()
        
        self.ip = self.build_law_conform_ip(ip)
        self.ip_info = self.worker.client.cftools_resolve_ip(self.ip)

    @property
    def country_name(self):
        return self.ip_info.get('country_name')
        
    @property
    def country_code(self):
        return self.ip_info.get('country_code')
        
    def fix_name(self, name):
        return ''.join([i if ord(i) < 128 else ' ' for i in name])
        
    def build_law_conform_ip(self, ip):
        # anonymize ip e.g.
        # 1.1.1.34 (unique ip) -> 1.1.1.0 (broadcast address)
        splitted_ip = ip.split('.')
        for _ in range(4-len(splitted_ip)):
            splitted_ip.append('1')
        splitted_ip[3] = '0'
        ip = '.'.join(splitted_ip)
        return ip
        
    def __del__(self):
        playtime = time() - self.session_start
        if self.omega_id:
            self.worker.client.api.update_player_state(self.omega_id, state=False, server_id=self.worker.server_id, kicked=self.kicked, reason=self.reason, playtime=playtime)

    def set_guid(self, guid):
        self.guid = guid
        self.process_player_data()
        
        if self.kicked:
            return
        
        if self.omega_id:
            self.worker.client.api.update_player_state(self.omega_id, state=True, server_id=self.worker.server_id, ip=self.ip, name=self.name, guid=self.guid)
            
        if self.worker.config.get('whitelist_enabled'):
            self.check_whitelist()
            
        self.check_globalban()
        self.check_ban()
        
        if self.kicked:
            return
        
        self.check_permission_level()

    def process_player_data(self):
        timestamp = int(time())
        player_data = {
            'be_guid': self.guid,
            'last_ip': self.ip,
            'names': [self.name],
            'last_seen': timestamp,
            'first_seen': timestamp,
            'history': [],
            'steamid': '',
            'origin_client': self.worker.client.client_id,
            'globalban': {
                'status': False,
                'enforceable': True,
                'reason': '',
                'timestamp': 0,
                'authorized_by': 'CFTools Staff'
            },
            'active_server': self.worker.server_id
        }
        response = self.worker.client.api.player_query(self.guid, self.worker.server_id, self.worker.container)
        if not response.get('success'):
            response = self.worker.client.api.player_create(self.guid, player_data)
            self.player_data = player_data
            self.server_data = None
            if not response.get('success') or 'omega_id' not in response.get('data'):
                self.worker.trigger_callback('tool', 'error', '{}: omega_id for {} could not be retrieved, please contact an administrator'.format(self.name, self.guid))
                return self.kick('[CFTools] Corrupted player information')
                
            self.omega_id = response.get('data').get('omega_id')
            steamid = response.get('data').get('steamid')
            steam_profile = self.worker.client.steam.profile(steamid)
            self.steam = steam_profile
            self.say(FIRST_TIME_MESSAGES)
                
        else:
            self.player_data = response.get('data').get('player')
            if 'terminated' in self.player_data:
                self.worker.trigger_callback('tool', 'error', '{}: Account has been terminated'.format(self.name))
                return self.kick('[CFTools] Account terminated. Server access denied.') 
                
            self.server_data = response.get('data').get('server')
            self.omega_id = response.get('data').get('omega_id')
            if self.worker.client.steam.available and self.player_data.get('steamid'):
                steam_profile = self.worker.client.steam.profile(self.player_data.get('steamid'))
                self.steam = steam_profile
                self.steam_profile_state = 'public' if steam_profile['communityvisibilitystate'] == 3 else 'private'
                # playtime = self.worker.client.steam.gametime(self.player_data.get('steamid'))
                playtime = False # Will be a restricted feature. Needs way to much resources depending on how many games a player has/plays
                if playtime:
                    self.dayz_playtime = playtime.get('playtime_forever')/60
                    
                else:
                    self.dayz_playtime = -1
            
    def check_ban(self):
        if self.omega_id and self.server_data:
            ban_data = self.server_data.get('banned_state')
            
            if ban_data:
                self.kick('You are banned from this server! ({})'.format(ban_data.get('reason')))
                
    def check_globalban(self):
        if self.player_data.get('globalban').get('status'):
            if self.worker.config.get('accept_globalbans'):
                self.kick('CFTools Globalban ({})'.format(self.player_data.get('globalban').get('reason')))
                
            elif self.player_data.get('globalban').get('enforceable'):
                self.kick('[ENFORCED] CFTools Globalban ({})'.format(self.player_data.get('globalban').get('reason')))
                
    def check_whitelist(self):
        if self.worker.hive != 'private':
            return self.worker.trigger_callback('tool', 'error', 'Whitelist enabled but hive Public')
        
        if self.omega_id and self.server_data:
            whitelist_data = self.server_data.get('whitelist_state')
            
            if whitelist_data:
                if whitelist_data.get('expires') != -1:
                    if time() > whitelist_data.get('expires'):
                        self.kick('You are not listed on this servers whitelist')
                        
    # TODO: Make CFTools Staff permissions opt-out
    # - When opting out no official support will be provided for that server/tool/account
    def check_permission_level(self):
        if self.omega_id and self.server_data:
            self.permission_level = self.server_data.get('admin_state').get('level') if self.server_data.get('admin_state') else 'player'
            if self.player_data.get('steamid'):
                if self.player_data.get('steamid') in self.worker.client.cftools_staff:
                    self.permission_level = 'cftools_staff'

        else:
            self.permission_level = 'player'
                
    def kick(self, reason='You have been kicked from the server'):
        self.kicked = True
        self.reason = self.construct_message(reason)
        if self.worker.hive == 'private':
            self.worker.server.kick_player(self.slot, self.reason)
            
        else:
            message = u'[CFTools] {} has been kicked for: {}'.format(self.name, self.reason)
            self.worker.server.say_all(message)
            self.worker.server.kick_name(self.name)
            self.worker._fake_kick_event(self)
        
    def say(self, message=''):
        message = self.construct_message(message)
        self.worker.server.say_player(self.slot, message)

    def construct_message(self, message):
        message = str(message)
        message = message.replace('%NAME%', self.name) 
        message = message.replace('%IP%',   self.ip)
        message = message.replace('%GUID%', self.guid)
        message = message.replace('%OMEGAID%', self.omega_id)
        message = message.replace('%RANK%', self.permission_level.capitalize())
        message = message.replace('%PING%', str(self.ping))
        message = message.replace('%SLOT%', str(self.slot))
        message = message.replace('%COUNTRY%', self.country_name)
        if self.worker.servername:
            message = message.replace('%SERVERNAME%', self.worker.servername)
            message = message.replace('%HIVE%', self.worker.hive) 
            message = message.replace('%MAXPLAYERS%', str(self.worker.max_players))
        return message
