import socket
import threading
import struct
import binascii
import time
import re

BUFFER_SIZE = 1024*4


class BattleEyeRconProtocol(object):
    def __init__(self, host, port, password):
        self.socket = None
        self.host = host
        self.port = port
        self.password = password

    def login(self):
        message = self.build_message(self.password, 'login')
        self.socket.send(message)
        
    def command(self, command):
        message = self.build_message(command, 'cmd')
        self.socket.send(message)
        
    def acknowledge(self, sequence):
        message = self.build_message(str(sequence), 'acknowledge')
        self.socket.send(message)
        
    def keepalive(self):
        message = self.build_message('', 'keepalive')
        self.socket.send(message)

    def recieve_data(self):
        data = self.socket.recv(BUFFER_SIZE)
        return data
                
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect((self.host, self.port))
        self.socket.settimeout(45)

    def decode_data(self, data):
        response = {
            'message_type': -1, 
            'sequence': -1, 
            'data': ''
        }
	    
        if data[0:2] != b'BE':
        	return response

        response['message_type'] = ord(data[7:8])
        response['sequence'] = ord(data[8:9])
        response['data'] = data[9:]
        
        self.acknowledge(data[8:9])
        
        return response
        
    def compute_crc(self, data):
        buf = memoryview(data)
        crc = binascii.crc32(buf) & 0xffffffff
        crc32 = '0x%08x' % crc
        return int(crc32[8:10], 16), int(crc32[6:8], 16), int(crc32[4:6], 16), int(crc32[2:4], 16)
        
    def build_message(self, data='', message_type='cmd'):
        message = bytearray()
        message.append(0xFF)

        if message_type == 'login':
            header = 0x00
            
        elif message_type == 'cmd' or message_type == 'keepalive':
            header = 0x01
            
        elif message_type == 'acknowledge':
            header = 0x02

        message.append(header)

        if header == 0x01:
            message.append(0x00)

        if data:
            message.extend(data.encode('utf-8', 'replace'))

        data = bytearray(b'BE')
        data.extend(self.compute_crc(message))
        data.extend(message)
        return data
