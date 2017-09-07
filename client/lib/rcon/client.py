import socket
import threading
import struct
import binascii
import time
import re

from lib.callback import Callback
from lib.rcon.protocol import BattleEyeRconProtocol


class BattleEyeRcon(threading.Thread, Callback):
    #TODO: move this somewhere else?
    _regex = {
        'player_guid': {
            'regex': r'Verified GUID \((.*)\) of player #([0-9]+) (.*)',
            'identification_string': ['Verified GUID']
        },
        'player_unverified_guid': {
            'regex': r'Player #([0-9]+) (.*) - GUID: (.*)',
            'identification_string': ['Player #', 'GUID:']
        },
        'player_disconnect': {
            'regex': r'Player #([0-9]+) (.*) disconnected',
            'identification_string': ['Player #', 'disconnected']
        },
        'player_connect': {
            'regex': r'Player #([0-9]+) (.*) \((.*):(.*)\) connected',
            'identification_string': ['Player #', ') connected']
        },
        'player_list': {
            'regex': r'(\d+)\s+(.*?)\s+([0-9]+)\s+([A-z0-9]{32})\(.*?\)\s(.*)\s\((.*)\)',
            'identification_string': ['Players on server:']
        },
        'be_kick': {
            'regex': r'\((.*)\) has been kicked by BattlEye: (.*) \((.*)\)',
            'identification_string': ['has been kicked by BattlEye']
        },
        'rcon_message': {
            'regex': r'RCon admin #([0-9]+): \((.*)\) (.*)',
            'identification_string': ['RCon admin #', ': ']
        },
        'rcon_admin_login': {
            'regex': r'RCon admin #([0-9]+) \((.*)\) logged in',
            'identification_string': ['RCon admin #', 'logged in']
        },
        'unable_to_recieve': {
            'regex': r'(.*)',
            'identification_string': ['Player is unable to receive the message']
        },
        'connected_be_master': {
            'regex': r'(.*)',
            'identification_string': ['Connected to BE Master']
        }
    }

    def __init__(self, host, port, password):
        threading.Thread.__init__(self)
        
        self._keepalive_interval = 10
        self._authenticated = None

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
        
        self.create_callbacks('event', [
            'player_guid',
            'player_unverified_guid',
            'player_connect',
            'player_disconnect',
            'player_list',
            'be_kick',
            'player_chat',
            'rcon_message',
            'rcon_admin_login',
            'unable_to_recieve',
            'connected_be_master'
        ])
        
        self.create_callbacks('error', [
            'critical',
            'connection_refused',
            'connection_closed'
        ])
        
        self.alive = time.time()
        self.running = False
        
        self.host = str(host)
        self.port = int(port)
        self.password = password
        self.rcon = BattleEyeRconProtocol(self.host, self.port, self.password)
        self.setDaemon(True)
        
        self.register_callback('connection', 'authenticated', self._callback_authenticated)
        self.register_callback('connection', 'authentication_failed', self._callback_authentication_failed)
        self.register_callback('connection', 'keepalive_acknowledged', self._callback_keepalive_acknowledged)
        self.register_callback('data', 'recieved', self._callback_data_recieved)

    def shutdown_server(self):
        self.rcon.command('shutdown')

    def restart_server(self):
        self.rcon.command('restartserver')
        
    def request_playerlist(self):
        self.rcon.command('players')

    def kick_player(self, slot, reason='You have been kicked from the server'):
        command = 'kick {} {}'.format(slot, reason)
        self.rcon.command(command)

    def say_all(self, message, slot=-1):
        command = 'say {} {}'.format(slot, message)
        self.rcon.command(command)

    def say_player(self, slot, message):
        command = 'say {} {}'.format(slot, message)
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
        
    def checkalive(self):
        if time.time()-self.alive >= 30:
            self.stop()
            while self.running:
                time.sleep(.05) #wait for thread to exit (50 ms)

            return self.trigger_callback('error', 'connection_closed')
            
    def keepalive(self):
        self.rcon.keepalive()

    def stop(self):
        self._active = False
        
    def run(self):
        self._active = True
        timeouts = 0
        retries = 0
        multipacket = {
            'count': 0,
            'current': 0,
            'data': ''
        }
        self.running = True
        while self._active:
            try:
                raw_data = self.rcon.recieve_data()

            except socket.timeout as e:
                if not self._authenticated:
                    timeouts += 1
                    
                    if timeouts >= 60:
                        timeouts = 0
                        retries += 1
                        self.rcon.connect()
                        self.rcon.login()
                        
                    if retries >= 60:
                        return self.trigger_callback('error', 'connection_refused')

                continue
            
            except socket.error as e:
                if e.errno == 111:
                    self.stop()
                    return self.trigger_callback('error', 'connection_refused')

            except Exception as e:
                try:
                    self.trigger_callback('error', 'error', 'error during recieving ({}, raw: {})'.format(e, raw_data))
                    
                except UnboundLocalError as another_e:
                    self.trigger_callback('error', 'error', another_e)
    
            try:
                response = self.rcon.decode_data(raw_data)
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
                if self._authenticated == None:
                    if response.get('sequence') == 1:
                        self.trigger_callback('connection', 'authenticated')

                    else:
                        self.trigger_callback('connection', 'authentication_failed')
                        
            elif response.get('message_type') == 1:
                if response.get('sequence') == 0 and not response.get('data'):
                    self.trigger_callback('connection', 'keepalive_acknowledged')

                else:
                    self.trigger_callback('data', 'recieved', response.get('data'))
                    
            elif response.get('message_type') == 2:
                self.trigger_callback('data', 'recieved', response.get('data'))

            else:
                print response

        self.running = False
	                
    def _callback_keepalive_acknowledged(self, *_):
        self.alive = time.time() 

    def _callback_authenticated(self, *_):
        self._authenticated = True
        self.request_playerlist()

    def _callback_authentication_failed(self, *_):
        self._authenticated = False

    def _callback_data_recieved(self, data):
        regex_chat = r'\((.*)\) (.*): (.*)'
        regex_lobby = r'(\d+)\s+(.*?)\s(.*?)\s+([A-z0-9]{32})\(.*?\)\s(.*)\s\((.*)\)'
        regex_ingame = r'(\d+)\s+(.*?)\s(.*?)\s+([A-z0-9]{32})\(.*?\)\s(.*)'
        for event_type, event in self._regex.iteritems():
            valid = True
            for identification_string in event.get('identification_string'):
                if identification_string not in data:
                    valid = False
                    break
            
            if not valid:
                continue

            else:
                if event_type == 'player_list':
                    players = []
                    player_list = data.split('\n')
                    del player_list[0:3]
                    del player_list[-1]
                    
                    for player in player_list:
                        try:
                            player_data = re.search(regex_lobby, player).groups()
                            lobby = True
                        
                        except Exception as e:
                            try:
                                player_data = re.search(regex_ingame, player).groups()
                                lobby = False
                                
                            except Exception as e:
                                continue
                            
                        try:
                            players.append({
                                'slot': player_data[0],
                                'ip': player_data[1].split(':')[0],
                                'ping': int(player_data[2]),
                                'guid': player_data[3],
                                'name': player_data[4],
                                'lobby': lobby
                            })
                        except:
                            continue
                        
                    return self.trigger_callback('event', event_type, players)
                    
                else:
                    try: #TODO: sometimes still exceptions so continue debugging
                        event_data = re.search(event.get('regex'), data).groups()
                        return self.trigger_callback('event', event_type, event_data)
                        
                    except Exception as e:
                        print event_type
                        print e
                        continue
                    
        try:
            chat_data = re.search(regex_chat, data).groups()
            return self.trigger_callback('event', 'player_chat', chat_data)
            
        except Exception as e:
            print 'unknown data: {} ({})'.format(data, e)
