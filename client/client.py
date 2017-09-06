#
# CFTools Omega
# Version: 2.0
# Copyright (c) 2017 Philipp Joos
# All rights reserved.
# 
# Location data by IPHub (https://iphub.info)
#

import threading
from time import time, sleep
import os

from api.steam import SteamAPI
from api.omega import OmegaAPI
from api.iphub import IPHubAPI

from lib.worker import OmegaWorker
from lib.callback import Callback
from lib.observer import OmegaObserver

ERROR_MODE = 1
CRITICAL_SERVICES = [
    'api', 
    'omega_master', 
    'cloud_configuration'
]


class OmegaClient(threading.Thread):
    def __init__(self, client_id, client_key, steam_api_key = '', iphub_api_key = ''):
        threading.Thread.__init__(self)
        self.client_id = client_id
        print '\033[1m{} starting up...'.format(self.client_id)     
        
        print 'Initialized observer'
        self.observer = OmegaObserver(self)
        
        self.workers = {}
        self.servers = {}
 
        self.api = OmegaAPI(identity=client_id, key=client_key, error_mode=ERROR_MODE)
        
        print 'Registering @ licensing server...'
        if not self.api.register().get('success'):
            print 'Could not register. Shutting down'
            raise SystemExit
            
        self.iphub = IPHubAPI(iphub_api_key)
        self.steam = SteamAPI(steam_api_key)
        
        print 'Retrieving client information...'
        response = self.api.client_start(self.client_id)
    
        if not response.get('success'):
            print 'Error retrieving initial server list. Shutting down'
            raise SystemExit
    
        else:
            print 'Setting up servers...'
            
        self._setup_servers(response.get('data').get('servers'))     
        
        print 'Client setup finished. Started. Waiting for orders from master...\033[0m'
        self.setDaemon(True)
        self.start()
        
    def _setup_servers(self, servers):
        for server_id, server in servers.iteritems():
            self._setup_server(server_id, server)
            
    def _setup_server(self, server_id, server):
        self.servers[server_id] = server
        
        if not server.get('stopped'):
            self.workers[server_id] = OmegaWorker(server_id, server, self)

    def run(self):
        while True:
            try:
                response = self.api.client_poll(self.client_id)
                
            except:
                continue

            if response.get('success'):
                orders = response.get('data').get('orders')
                
        self.api.client_stop(self.client_id)    
        
    def kill_worker(self, server_id, reason='shutdown'):
        if server_id not in self.workers:
            return
        
        self.workers[server_id].stop(reason)
        del self.workers[server_id]
        del self.servers[server_id]
        
    def restart_worker(self, server_id):
        config = self.servers.get(server_id)
        self.kill_worker(server_id)
        self._setup_server(server_id, config)
