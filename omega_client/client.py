import requests
import socket
import time
import threading

from cexceptions import *
from worker import OmegaWorker

LOCAL_CONFIG_PATH = '/var/omega-config/'

"""

Will be finished when the DayZ SA server files are being released.
"""

class OmegaClient(object):
    host = ''
    port = 24002
    protocol = 'http'
    
    access_token = ''
    
    servers = {}
    
    status = {}
    
    def __init__(self, client_id, host='philippj.de', port=24002, protocol='http', serverlist=[]):
        self.host = host
        self.port = port
        self.protocol = protocol
        
        self.client_id = client_id
        self.register()
        self.retrieve_service_status()
        if not serverlist:
            self.retrieve_assigned_servers()
        else:
            self.verify_serverlist(serverlist)
        
    def _build_url(self, endpoint='', val='', action='', special=''):
        if special:
            return '{}://{}:{}/{}'.format(
                    self.protocol, 
                    self.host, 
                    self.port,
                    special
                )
            
        else:
            return '{}://{}:{}/{}/{}/{}'.format(
                    self.protocol, 
                    self.host, 
                    self.port,
                    endpoint, 
                    val,
                    action
                )
                
    def request(self, endpoint, val, action, data = None, special=''):
        response = requests.get(
            self._build_url(endpoint, val, action, special),
            headers={'Authorization': 'Bearer {}'.format(self.access_token)},
            data=data
            ).json()
            
        if not response.get('success') and response.get('error_message') == 'expired token':
            self.register()
            return self.request(endpoint, val, action, data)
            
        return response
        
    def register(self):
        response = self.request('auth', self.client_id, 'register')
        if response.get('success'):
            self.access_token = response.get('access_token')
        else:
            raise OmegaAuthenticationError('invalid access_token')

        if self.request('auth', self.client_id, 'whoami').get('success'):
            return True
        
        else:
            raise OmegaAuthenticationError('error verifying access_token')
        
    def retrieve_service_status(self):
        critical = ['api', 'omega_master', 'cloud_configuration']
        response = self.request('', None, '', None, 'status')
        
        self.status = response.get('status')
        for service in self.status:
            if service in critical:
                if self.status.get(service) != 'online':
                    raise OmegaClientError('Critical service "{}" is {}'.format(service, self.status.get(service)))
        
        
    def verify_serverlist(self, serverlist):
        servers = []
        for server in serverlist:
            response = self.request('server', server, 'verify')
            if response.get('verified'):
                servers.append(server)
                
            else:
                print 'unknown server_id: {}'.format(server)
                
        self.load_servers(servers)
            
    def retrieve_assigned_servers(self):
        response = self.request('client', self.client_id, 'my_servers')

        if response.get('success'):
            self.load_servers(response.get('data').get('server_list'))
            
        else:
            raise OmegaAPIError('could not retrieve server_list')

    def load_servers(self, serverlist):
        for server in serverlist:
            self.servers[server] = Thread(target=OmegaWorker, name="workerthread-{}".format(server), args=(server, self,))
            self.servers[server].setDaemon(True)
            self.servers[server].start()
		    
    def retrieve_config(self, server_id):
        response = self.request('server', server_id, 'config')

        if response.get('success'):
            return response.get('data').get('config')
            
        else:
            return None
        
