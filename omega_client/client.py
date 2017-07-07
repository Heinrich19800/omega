import requests
import socket
import time
import threading
import json

from cexceptions import *
from worker import OmegaWorker


LOCAL_CONFIG_PATH = '/var/omega-config/'

"""

Will be finished on release of the DayZ SA server files
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
        #else:
        #    self.verify_serverlist(serverlist)
        
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
                
    def request(self, endpoint, val, action, payload = {}, special=''):
        try:
            response = requests.post(
                self._build_url(endpoint, val, action, special),
                headers={
                    'Authorization': 'Bearer {}'.format(self.access_token), 
                    'client_id': self.client_id
                },
                json=payload
                ).json()
        
        except requests.exceptions.ConnectionError as e:
            #TODO: further error handling needed
            # - shutdown client instance?
            # - loop till connection established?
            # - block requests till connection reestablished?
            raise Exception('Cant connect to licensing server') 
        
        if not response.get('success') and response.get('error_message') == 'expired token':
            self.register()
            return self.request(endpoint, val, action, payload)
            
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
            self.servers[server] = threading.Thread(target=OmegaWorker, name="workerthread-{}".format(server), args=(server, self,))
            self.servers[server].setDaemon(True)
            self.servers[server].start()
		    
    def retrieve_config(self, server_id):
        response = self.request('server', server_id, 'config')

        if response.get('success'):
            return response.get('data').get('config')
            
        else:
            return None
            
    def _worker_reinitiate(self, server_id, reason=''):
        if server_id not in self.servers:
            return
        
        print '[WorkerThread-{}] Reinitiate due to: {}'.format(server_id, reason)
    
        del self.servers[server_id]
        self.servers[server_id] = threading.Thread(target=OmegaWorker, name="workerthread-{}".format(server_id), args=(server_id, self,))
        self.servers[server_id].setDaemon(True)
        self.servers[server_id].start()
        
    def _server_offline(self, server_id):
        self.request('server', server_id, 'state', {'state': 0})
    
    def _server_online(self, server_id):
        self.request('server', server_id, 'state', {'state': 2})
    
    def _server_started(self, server_id):
        self.request('server', server_id, 'state', {'state': 1})
    
