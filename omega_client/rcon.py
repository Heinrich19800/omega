import socket
import threading

"""

Will be finished on release of the DayZ SA server files
"""

class BattleEyeRcon(threading.Thread):
    _sequence = 0
    _socket = None
    _buffer_size = 4096
    _keepalive_interval = 15
    _authenticated = False
    
    host = ''
    port = 0
    password = ''
    
    _callbacks = {
       
    }
    
    def __init__(self, host, port, password):
        threading.Thread.__init__(self)
        
        self.host = host
        self.port = port
        self.password = password
        
    def recieve_data(self):
        if not self._socket:
            raise BattleEyeRconError('recieve_data called before has been connection established')
            
        data = self._socket.recv(self._buffer_size)
        return data
        
    def build_login_data(self):
        data = '\xFF\x00{}'.format(self.password)
        return 'BE{}{}'.format(self._generate_checksum_str(data), data)
        
    def _generate_checksum(self, data):
        return struct.pack('1', binascii.crc32(data) & 0xffffffff)[:4]
        
    def build_message(self, data='', message_type='cmd', keepalive=False, sequence=None):
        message = '\xFF'
        
        if message_type == 'login':
            header = '\x00'
            
        elif message_type == 'cmd':
            header = '\x01'
            
        elif message_type == 'acknowledge':
            header = '\x02'
            
        if keepalive:
            message += '\x01{}'.format(chr(self._sequence))
            self._sequence += 1
            
        elif sequence:
            message += '\x02{}'.format(chr(sequence))
            
        else:
            message += '{}{}{}'.format(header, chr(self._sequence), data)
            self._sequence += 1
        
        checksum = self._generate_checksum(message)
        return 'BE{}{}'.format(checksum, message)
        
    def connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect((self.host, self.port))
        self._socket.settimeout(5)
		
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
        
        recieved_crc = data[2:6]
        
        if recieved_crc != self._generate_checksum(data[6:]):
        	raise BattleEyeRconError('invalid crc')
        
        response['message_type'] = ord(packet[7:8])
        response['sequence'] = ord(packet[8:9])
        response['data'] = packet[9:]
        return response
        
    def run(self):
        self._active = True
        self._keepalive_thread = Thread(target=self.keepalive_thread, name="keepalive")
        self._keepalive_thread.setDaemon(True)
        
        while self._active:
            response = self._decode_data(self.recieve_data())
            if response.get('message_type') == 0:
                if response.get('sequence') == 1:
                    if not self._authenticated:
                        self._authenticated = True
                        self._keepalive_thread.start()
                    
                else:
                    raise BattleEyeRconError('login failed')
                    
            elif response.get('message_type') == 1:
                if response.get('data')[0:1] == chr(0):
                    pass #multipacket
                
                else:
                    pass #command response
                    
            elif response.get('message_type') == 2:
                message = self.build_message('', 'acknowledge', False, response.get('sequence'))
                self._socket.send(message)
	                
    def keepalive(self):
        while self._active:
            message = self.build_message('', 'cmd', True)
            self._socket.send(message)
            time.sleep(self._keepalive_interval)