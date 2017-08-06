#
# CFTools Omega
# Version: 0.01
#
import requests
import socket
import time
import threading
import json
import urllib2

from cexceptions import *
from worker import OmegaWorker

LOCAL_CONFIG_PATH = '/var/omega-config/'

"""
TODO:
- polling in client?
- move api stuff to another file/class
- better error handling for failed master requests
- load avg., cpu usage, mem usage monitoring for dynamic loadbalancing
"""

class OmegaClient(object):
    host = ''
    protocol = 'https'
    
    access_token = ''
    
    servers = {}
    
    status = {}
    
    def __init__(self, client_id, host='cfbackend.de', protocol='https', serverlist=[], steam_api_key = ''):
        self.host = host
        self.protocol = protocol
        self.steam_api_key = steam_api_key
        
        self.ping(max_retries=5)
        
        self.client_id = client_id
        self.register()
        self.retrieve_service_status()
    
        while True:
            if not serverlist:
                self.retrieve_assigned_servers()
    
            #TODO: implement back independent mode
            #else:
            #    self.verify_serverlist(serverlist)
            time.sleep(60*5)
        
    def _build_url(self, endpoint='', val='', action='', special=''):
        if special:
            return '{}://{}/{}'.format(
                    self.protocol, 
                    self.host,
                    special
                )
            
        else:
            return '{}://{}/{}/{}/{}'.format(
                    self.protocol, 
                    self.host,
                    endpoint, 
                    val,
                    action
                )
                
    def request(self, endpoint, val, action, payload = {}, special='', timeout=60):
        try:
            response = requests.post(
                self._build_url(endpoint, val, action, special),
                headers={
                    'Authorization': 'Bearer {}'.format(self.access_token), 
                    'client_id': self.client_id
                },
                json=payload,
                timeout=timeout
                )
            response = response.json()
        
        except requests.exceptions.ConnectionError as e:
            #TODO: further error handling needed
            # - shutdown client instance?
            # - loop till connection established?
            # - block requests till connection reestablished?
            raise Exception('Cant connect to licensing server') 
            
        except ValueError as e:
            raise Exception('JSON error: {}'.format(response))
        
        if not response.get('success') and response.get('error_message') == 'expired token':
            self.register()
            return self.request(endpoint, val, action, payload)
            
        return response
        
    def ping(self, max_retries=1):
        retries = 0
        
        while retries < max_retries:
            try:
                response = requests.get(self._build_url(special=' ')).json()
                
            except Exception:
                time.sleep(2)
                continue
            
            return
        
        raise OmegaAuthenticationError('Could not reach licensing server')
        
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
            if server not in self.servers:
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
    
        if self.servers[server_id].get('stopped'):
            self._worker_kill(server_id, 'stopped')
    
        del self.servers[server_id]

        self.servers[server_id] = threading.Thread(target=OmegaWorker, name="workerthread-{}".format(server_id), args=(server_id, self,))
        self.servers[server_id].setDaemon(True)
        self.servers[server_id].start()
        
    def _worker_kill(self, server_id, reason=''):
        if server_id not in self.servers:
            return
        
        print '[WorkerThread-{}] Killed due to: {}'.format(server_id, reason)
    
        del self.servers[server_id]
        
    def _server_offline(self, server_id, reason):
        self.request('server', server_id, 'state', {'state': 0, 'reason': reason})
    
    def _server_online(self, server_id):
        self.request('server', server_id, 'state', {'state': 2})
    
    def _server_started(self, server_id):
        self.request('server', server_id, 'state', {'state': 1})
        
    def steam_profile_request(self, steamid):
        if not self.steam_api_key:
            return {}
            
        options = {
            'key': self.steam_api_key,
            'steamids': steamid
        }
        url = 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0001/?key={}&steamids={}'.format(options.get('key'), options.get('steamids'))
        rv = json.load(urllib2.urlopen(url))
        return rv['response']['players']['player'][0] or {}
    
