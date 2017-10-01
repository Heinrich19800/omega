import socket
import threading
import struct
import binascii
import time
import re

from lib.callback import Callback
from lib.rcon.protocol2 import BattleEyeRconProtocol

RCON_REGEX_LIST = {
    # Player events
    'player_connect': r'Player #([0-9]+) (.*) \((.*):(.*)\) connected',
    'player_disconnect': r'Player #([0-9]+) (.*) disconnected',
    'player_guid': r'Verified GUID \((.*)\) of player #([0-9]+) (.*)',
    'player_unverified_guid': r'Player #([0-9]+) (.*) - GUID: (.*)',
    'player_unable_to_recieve': r'Player is unable to receive the message',
    'player_chat': r'\((.*)\) (.*): (.*)',

    # Playerlist
    'player_list': r'Players on server:',
    
    # BattleEye events
    'be_kick':  r'\((.*)\) has been kicked by BattlEye: (.*)',
    'be_master_connected': r'Connected to BE Master',
    'be_master_disconnected': r'Disconnected from BE Master',
    'be_master_connect_error': r'Could not connect to BE Master',
    'be_master_failed_recv': r'Failed to receive from BE Master',
    'be_master_failed_send': r'Failed to send to BE Master',
    
    # Rcon events
    'rcon_message': r'RCon admin #([0-9]+): \((.*)\) (.*)',
    'rcon_admin_login': r'RCon admin #([0-9]+) \((.*)\) logged in'
}

RCON_PLAYERLIST_REGEX_EXTRA = {
    'player_list_lobby': r'(\d+)\s+(.*?)\s(.*?)\s+([A-z0-9]{32})\(.*?\)\s(.*)\s\((.*)\)',
    'player_list_ingame': r'(\d+)\s+(.*?)\s(.*?)\s+([A-z0-9]{32})\(.*?\)\s(.*)'
}

class DayZServer(Callback):
    def __init__(self, host, port, password):
        self.authenticated = None
        self.running = False
        self.active = True
        self.alive = time.time()

        self.create_callbacks('connection', [
            'lost',
            'authenticated',
            'authentication_failed',
            'keepalive_acknowledged'
        ])
        
        self.create_callbacks('data', [
            'recieved',
            'sent'
        ])
        
        self.create_callbacks('event', RCON_REGEX_LIST.keys())
        
        self.create_callbacks('error', [
            'error',
            'critical',
            'connection_refused',
            'connection_closed',
            'checkalive_failed'
        ])
        
        self.register_callback('connection', 'authenticated', self._callback_authenticated)
        self.register_callback('connection', 'authentication_failed', self._callback_authentication_failed)
        self.register_callback('connection', 'keepalive_acknowledged', self._callback_keepalive_acknowledged)
        self.register_callback('data', 'recieved', self._callback_data_recieved)
        
        self.host = str(host)
        self.port = int(port)
        self.password = password
        self.rcon = BattleEyeRconProtocol(self.host, self.port, self.password)
        self.spawn_listener()
        
    def keepalive(self):
        self.rcon.keepalive()

    def spawn_listener(self):
        self.listener = threading.Thread(target=self.run)
        self.listener.setDaemon(True)

    def stop(self):
        self.active = False
        tmstp = int(time.time())
        while self.running:
            time.sleep(1)

    def start(self):
        if not self.active:
            self.spawn_listener()
            self.active = True
            self.authenticated = None

        self.listener.start()
        
    def run(self):
        timeouts = 0
        retries = 0
        multipacket = {
            'count': 0,
            'current': 0,
            'data': ''
        }
        self.running = True
        self.rcon.connect()
        self.rcon.login()
        while self.active:
            try:
                raw_data = self.rcon.recieve_data()

            except socket.timeout as e:
                if not self.active:
                    break
                
                self.async_trigger_callback('error', 'checkalive_failed')
                continue
            
            except socket.error as e:
                if e.errno == 111:
                    self.async_trigger_callback('error', 'connection_refused')
                    break

            except Exception as e:
                try:
                    self.async_trigger_callback('error', 'error', 'error during recieving ({}, raw: {})'.format(e, raw_data))
                    
                except UnboundLocalError as another_e:
                    self.async_trigger_callback('error', 'error', another_e)
    
            try:
                response = self.rcon.decode_data(raw_data)
                try:
                    response['data'] = response['data'].decode("utf-8","replace")
                    
                except Exception, e:
                    print 'Encoding error: {}'.format(e)
                    print response['data']
                    continue
                
                if len(response.get('data')) > 0 and response.get('data')[0] == '\x00':
                    multipacket['count'] = int(ord(response.get('data')[1]))
                    multipacket['current'] = int(ord(response.get('data')[2]))+1
                    multipacket['data'] += response.get('data')[3:]
                    
                    if multipacket['count'] != multipacket['current']:
                        continue
                    
                    else:
                        response['data'] = multipacket['data']
                        multipacket['data'] = ''

            except Exception as e:
                continue
            
            if response.get('message_type') == 0:
                if self.authenticated == None:
                    if response.get('sequence') == 1:
                        self.async_trigger_callback('connection', 'authenticated')

                    else:
                        self.async_trigger_callback('connection', 'authentication_failed')
                        
            elif response.get('message_type') == 1:
                if response.get('sequence') == 0 and not response.get('data'):
                    self.async_trigger_callback('connection', 'keepalive_acknowledged')

                else:
                    self.async_trigger_callback('data', 'recieved', response.get('data'))
                    
            elif response.get('message_type') == 2:
                self.async_trigger_callback('data', 'recieved', response.get('data'))

            else:
                print response

        self.running = False
	                
    def _callback_keepalive_acknowledged(self, *_):
        self.alive = time.time() 

    def _callback_authenticated(self, *_):
        self.authenticated = True
        self.keepalive() # inital keepalive
        self.request_playerlist()

    def _callback_authentication_failed(self, *_):
        self.authenticated = False

    def _callback_data_recieved(self, data):
        for event_type, regex in RCON_REGEX_LIST.iteritems():
            try: #TODO: sometimes still exceptions so continue debugging
                event_regex_result = re.search(regex, data)
                if event_regex_result:
                    if event_type == 'player_list': 
                        event_data = data
                        
                    elif event_type in [
                                        'be_master_connected', 
                                        'be_master_disconnected', 
                                        'be_master_connect_error', 
                                        'be_master_failed_recv', 
                                        'be_master_failed_send']:
                    
                        event_data = data  
                        
                    else:
                        event_data = event_regex_result.groups()
                        
                    return self.trigger_callback('event', event_type, event_data)
                    

                
            except Exception as e:
                print event_type
                print e
                continue
                
        print u'unknown data: {} '.format(data)
        
    def shutdown(self):
        self.rcon.command('shutdown')

    def restartserver(self):
        self.rcon.command('#restartserver')
        
    def request_playerlist(self):
        self.rcon.command('players')
        
    def request_adminlist(self):
        self.rcon.command('admins')
        
    def monitor(self, interval):
        self.rcon.command('monitor {}'.format(interval))

    def kick_player(self, slot, reason='You have been kicked from the server'):
        command = u'kick {} {}'.format(slot, reason)
        self.rcon.command(command)
        
    def kick_name(self, name): # Kicking for public hives
        command = u'#kick {}'.format(name)
        self.rcon.command(command)
        
    def say_all(self, message, slot=-1):
        command = u'say {} {}'.format(slot, message)
        self.rcon.command(command)

    def say_player(self, slot, message):
        command = u'say {} {}'.format(slot, message)
        self.rcon.command(command)

    def rcon_ban_player(self, slot, reason, time=0):
        #rcon implementation not used for omega
        #time = temporary ban in minutes, 0=permanent ban (default)
        command = 'ban {} {} {}'.format(slot, time, reason)
        self.rcon.command(command)

    def rcon_ban_guid(self, guid, reason, time=0):
        #rcon implementation not used for omega
        #time = temporary ban in minutes, 0=permanent ban (default)
        command = 'addban {} {} {}'.format(guid, time, reason)
        self.rcon.command(command)

    def rcon_unban(self, banid):
        #rcon implementation not used for omega
        command = 'removeban {}'.format(banid)
        self.rcon.command(command)

    def rcon_updatebans(self):
        #rcon implementation not used for omega
        self.rcon.command('writebans')

    def rcon_loadbans(self):
        #rcon implementation not used for omega
        self.rcon.command('loadbans')