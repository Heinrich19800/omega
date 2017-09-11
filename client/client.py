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
from api.ip    import resolve_ip

from lib.worker import OmegaWorker
from lib.callback import Callback
from lib.observer import OmegaObserver

ERROR_MODE = 1
CRITICAL_SERVICES = [
    'api', 
    'omega_master', 
    'cloud_configuration'
]

# CFTools Steam GroupID
# Must be the primary group of the profile to provide Staff rights
CFTOOLS_STAFF_PERM_GROUP = '103582791459898589'


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
        self.cftools_resolve_ip = resolve_ip
        
        print 'Registering @ licensing server...'
        if not self.api.register().get('success'):
            print 'Could not register. Shutting down'
            raise SystemExit
            
        self.iphub = IPHubAPI()
        self.iphub.update_api_key(iphub_api_key)
        self.steam = SteamAPI(steam_api_key)
        
        self.cftools_staff = self.steam.retrieve_group_members(CFTOOLS_STAFF_PERM_GROUP)
        
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
        if not server.get('config').get('stopped'):
            self.start_worker(server_id)
            
    def _execute_orders(self, orders):
        for order in orders:
            if order.get('action') == 'start':
                server_id = order.get('server_id')
                self.servers[server_id]['config']['stopped'] = False
                self.start_worker(server_id)
                    
            elif order.get('action') == 'stop':
                server_id = order.get('server_id')
                self.servers[server_id]['config']['stopped'] = True
                
                if self.workers.get(server_id):
                    self.workers[server_id].server.stop()
                    self.kill_worker(server_id, 'web_shutdown')
                    
            elif order.get('action') == 'say_player':
                server_id = order.get('server_id')
                player = self.workers[server_id].get_player_by_omega_id(order.get('omega_id'))
                player.say(order.get('message'))
                
            elif order.get('action') == 'kick_player':
                server_id = order.get('server_id')
                player = self.workers[server_id].get_player_by_omega_id(order.get('omega_id'))
                player.kick(order.get('message'))
                
            elif order.get('action') == 'say_all':
                server_id = order.get('server_id')
                self.workers[server_id].server.say_all(order.get('message'))
                
            elif order.get('action') == 'cftoolsbroadcast':
                for server_id in self.workers:
                    message = '[CFTools Broadcast] {}'.format(order.get('message'))
                    self.workers[server_id].server.say_all(message)
                    
            elif order.get('action') == 'module':
                server_id = order.get('server_id')
                self.servers[server_id]['config']['modules'][order.get('module')] = order.get('config')
                self.workers[server_id].config['modules'][order.get('module')] = order.get('config')
                self.workers[server_id].trigger_callback('tool', 'module_update', order.get('module'))
                
    def run(self):
        while True:
            try:
                response = self.api.client_poll(self.client_id)
                
            except:
                continue

            if response.get('success'):
                orders = response.get('data').get('orders')
                self._execute_orders(orders)
                
        self.api.client_stop(self.client_id)    
        
    def kill_worker(self, server_id, reason='shutdown'):
        if server_id not in self.workers:
            return
        
        self.workers[server_id].stop(reason)
        
    def restart_worker(self, server_id):
        config = self.servers.get(server_id)
        self.kill_worker(server_id)
        self._setup_server(server_id, config)
        
    def start_worker(self, server_id):
        if server_id not in self.workers:
            self.workers[server_id] = OmegaWorker(server_id, self.servers[server_id], self)
        
        else:
            self.workers[server_id].start()
