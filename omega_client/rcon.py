import socket
import threading
import struct
import binascii
import time

"""

Will be finished on release of the DayZ SA server files
"""

class BattleEyeRconException(Exception):
    pass

class BattleEyeRcon(threading.Thread):
    _sequence = 0
    _socket = None
    _buffer_size = 1024
    _keepalive_interval = 30
    _authenticated = None
    
    host = ''
    port = 0
    password = ''
    
    _callbacks = {
       'connection': {
            'lost': [],
            'established': [],
            'authenticated': [],
            'authentication_failed': [],
            'keepalive_acknowledged': []
       },
       'data': {
            'recieved': [],
            'sent': []
       }
    }

    def __init__(self, host, port, password):
        threading.Thread.__init__(self)
        
        self.host = host
        self.port = port
        self.password = password
        self.setDaemon(True)

        self.register_callback('connection', 'authenticated', self._callback_authenticated)
        self.register_callback('connection', 'authentication_failed', self._callback_authentication_failed)

    def shutdown_server(self):
        self.command('#shutdown')

    def restart_server(self):
        self.command('#restartserver')

    def kick_player(self, slot):
        command = 'kick {}'.format(slot)
        self.command(command)

    def say_all(self, message, slot=-1):
        command = 'say {} {}'.format(slot, message)
        self.command(command)

    def say_player(self, message, slot):
        command = 'say {} {}'.format(slot, message)
        self.command(command)

    def rcon_ban_player(self, slot, reason, time=0):
        #rcon implementation not used for omega
        #time = temporary ban in minutes, 0=permanent ban (default)
        command = 'ban {} {} {}'.format(slot, time, reason)
        self.command(command)

    def rcon_ban_guid(self, guid, reason, time=0):
        #rcon implementation not used for omega
        #time = temporary ban in minutes, 0=permanent ban (default)
        command = 'addban {} {} {}'.format(guid, time, reason)
        self.command(command)

    def rcon_unban(self, banid):
        #rcon implementation not used for omega
        command = 'removeban {}'.format(banid)
        self.command(command)

    def rcon_updatebans(self):
        #rcon implementation not used for omega
        self.command('writebans')

    def rcon_loadbans(self):
        #rcon implementation not used for omega
        self.command('loadbans')

    def register_callback(self, endpoint, action, method_reference):
        if endpoint not in self._callbacks:
            raise BattleEyeRconException('Cant register callback for unknown endpoint "{}"'.format(endpoint))

        if action not in self._callbacks[endpoint]:
            raise BattleEyeRconException('Cant register callback for unknown action "{}.{}"'.format(endpoint, action))

        self._callbacks[endpoint][action].append(method_reference)

    def _trigger_callback(self, endpoint, action, data=None):
        for method in self._callbacks.get(endpoint).get(action):
            method(data) 
        
    def recieve_data(self):
        if not self._socket:
            raise BattleEyeRconException('recieve_data called before has been connection established')
            
        data = self._socket.recv(self._buffer_size)
        return data
                
    def _generate_crc(self, data):
        buf = memoryview(data)
        crc = binascii.crc32(buf) & 0xffffffff
        crc32 = '0x%08x' % crc
        return int(crc32[8:10], 16), int(crc32[6:8], 16), int(crc32[4:6], 16), int(crc32[2:4], 16)
        
    def build_message(self, data='', message_type='cmd', sequence=None):
        message = bytearray()
        message.append(0xFF)
        
        if message_type == 'login':
            header = 0x00
            
        elif message_type == 'cmd':
            header = 0x01
            
        elif message_type == 'acknowledge':
            header = 0x02

        elif message_type == 'keepalive':
            header = 0x01

        else:
            raise BattleEyeRconException('Invalid message_type provided')
                        
        message.append(header)

        if header == 0x01:
            message.append(0x00)

        if data:
            message.extend(data.encode('utf-8', 'replace'))

        data = bytearray(b'BE')
        data.extend(self._generate_crc(message))
        data.extend(message)
        return data

    def command(self, command):
        message = self.build_message(command)
        self._socket.send(message)
        print 'Send command: {}, ({})'.format(command, message)
        
    def connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect((self.host, self.port))
        self._socket.settimeout(5)
        self._trigger_callback('connection', 'established')
    	
    def login(self):
        message = self.build_message(self.password, 'login')
        self._socket.send(message)
        
    def stop(self):
        self._active = False
        
    def _compute_crc(self, data):
        buf = buffer(data)
        crc = binascii.crc32(buf) & 0xffffffff
        crc32 = '0x%08x' % crc
        return int(crc32[8:10], 16), int(crc32[6:8], 16), int(crc32[4:6], 16), int(crc32[2:4], 16)

    def _decode_data(self, data):
        response = {
            'message_type': -1, 
            'sequence': -1, 
            'data': ''
        }
	    
        if data[0:2] != b'BE':
        	return response

        else:
            message = self.build_message(data[8:9], 'acknowledge')
            self._socket.send(message)

        response['message_type'] = ord(data[7:8])
        response['sequence'] = ord(data[8:9])
        response['data'] = data[9:]
        return response
        
    def run(self):
        self._active = True
        self._keepalive_thread = threading.Thread(target=self.keepalive_thread, name="keepalive")
        self._keepalive_thread.setDaemon(True)

        
        while self._active:
            try:
                raw_data = self.recieve_data()
                response = self._decode_data(raw_data)

            except socket.timeout as e:
                continue

            except Exception as e:
                raise BattleEyeRconException('error during recieving')
              
            if response.get('message_type') == 0:
                if self._authenticated == None:
                    if response.get('sequence') == 1:
                            self._trigger_callback('connection', 'authenticated')

                    else:
                        self._trigger_callback('connection', 'authentication_failed')
                        
                else:
                    #multipacket, number of packets = sequence
                    print response
                    
            elif response.get('message_type') == 1:
                #command response
                if response.get('sequence') == 0 and not response.get('data'):
                    self._trigger_callback('connection', 'keepalive_acknowledged')

                else:
                    print response
                    
            elif response.get('message_type') == 2:
                print response

            else:
                print response
	                
    def keepalive_thread(self):
        while self._active:
            message = self.build_message('', 'cmd', True)
            self._socket.send(message)
            time.sleep(self._keepalive_interval)

    def _callback_authenticated(self, *_):
        print 'authenticated'
        self._keepalive_thread.start()
        self._authenticated = True

    def _callback_authentication_failed(self, *_):
        self._authenticated = False
        raise BattleEyeRconException('login failed')
        