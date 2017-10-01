import sys


class OrderManager(object):
    known_order_types = [
        # General
        'OrderCFToolsBroadcast',
        # Client
        'OrderStopTool',
        'OrderStartTool',
        # Worker/Player
        'OrderKick',
        'OrderSayPlayer',
        'OrderSayAll',
        # Worker notice
        'NoticeModuleConfigUpdate',
        'NoticeWorkerConfigUpdate', # not implemented
        'NoticeBanAdded'
    ]
    
    def __init__(self, client):
        self.client = client

    def get_order_class(self, order_type):
        return getattr(sys.modules[__name__], order_type)
    
    def verify_order_integrity(self, order):
        if 'type' not in order:
            return False
            
        if order.get('type') not in self.known_order_types:
            return False
        
        try:
            order_class = self.get_order_class(order.get('type'))
            
        except:
            return False
            
        instance = order_class(None, order, direct_execution=False)
        return instance.check_params(order)
        
    def process_order(self, order):
        if not self.verify_order_integrity(order):
            return 'integrity check failed' 
            
        order_class = self.get_order_class(order.get('type'))
        order = order_class(self.client, order)
        return True if order.error == None else order.error
    
    
class Order(object):
    required_params = []
    
    def __init__(self, client, data, direct_execution=True):
        self.client = client
        
        self.error = None

        if direct_execution:
            if not self.check_params(data):
                self.error = 'param check failed'
                
            else:
                self.fulfill_order(data)
            
    def fulfill_order(self, data):
        pass
    
    def check_params(self, data):
        for param in self.required_params:
            if param not in data:
                return False
                
        return True
    
class OrderCFToolsBroadcast(Order):
    required_params = ['message']
    
    def fulfill_order(self, data):
        message = '[CFTools Broadcast] {}'.format(data.get('message'))
        print '\033[1m {} \033[0m'.format(message)
        
        for _, worker in self.client.workers.iteritems():
            worker.server.say_all(message)

class OrderStartTool(Order):
    required_params = ['server_id']
    
    def fulfill_order(self, data):
        server_id = data.get('server_id')
        
        self.client.servers[server_id]['config']['stopped'] = False
        self.client.start_worker(server_id)
        
class OrderStopTool(Order):
    required_params = ['server_id']
    
    def fulfill_order(self, data):
        server_id = data.get('server_id')
        
        if server_id not in self.client.workers:
            self.error = 'server_id not found'
            return
        
        self.client.servers[server_id]['config']['stopped'] = True
        self.client.kill_worker(server_id, 'web_shutdown')
        
class OrderKick(Order):
    required_params = ['server_id', 'omega_id', 'message']
    
    def fulfill_order(self, data):
        server_id = data.get('server_id')
        
        if server_id not in self.client.workers:
            self.error = 'server_id not found'
            return
        
        player = self.client.workers[server_id].get_player_by_omega_id(data.get('omega_id'))
        if not player:
            self.error = 'player not found'
            return
        
        else:
            player.kick(data.get('message'))
            
class OrderSayAll(Order):
    required_params = ['server_id', 'message']
    
    def fulfill_order(self, data):
        server_id = data.get('server_id')
        
        if server_id not in self.client.workers:
            self.error = 'server_id not found'
            return
        
        message = data.get('message')
        self.client.workers[server_id].server.say_all(message)
        
class OrderSayPlayer(Order):
    required_params = ['server_id', 'message', 'omega_id']
    
    def fulfill_order(self, data):
        server_id = data.get('server_id')
        
        if server_id not in self.client.workers:
            self.error = 'server_id not found'
            return
        
        message = data.get('message')
        player = self.client.workers[server_id].get_player_by_omega_id(data.get('omega_id'))
        if not player:
            self.error = 'player not found'
            return
        
        else:
            player.say(message)
            
class NoticeModuleConfigUpdate(Order):
    required_params = ['server_id', 'config', 'module']
    
    def fulfill_order(self, data):
        server_id = data.get('server_id')
        if server_id not in self.client.workers:
            self.error = 'server_id not found'
            return
            
        self.client.servers[server_id]['config']['modules'][data.get('module')] = data.get('config')
        self.client.workers[server_id].config['modules'][data.get('module')] = data.get('config')
        self.client.workers[server_id].trigger_callback('tool', 'module_update', data.get('module'))
    
class NoticeBanAdded(Order):
    required_params = ['target', 'omega_id', 'reason']
    
    def fulfill_order(self, data):
        target = data.get('target')
        for server_id in self.client.workers:
            if target == 'cftoolsglobalban':
                #ol almighty banhammer has striked again
                player = self.client.workers[server_id].get_player_by_omega_id(data.get('omega_id'))
                if player:
                    player.kick('{}'.format(data.get('reason')))
                
            elif target == server_id or target == self.client.workers[server_id].container:
                player = self.client.workers[server_id].get_player_by_omega_id(data.get('omega_id'))
                if not player:
                    self.error = 'player not found'
                    return
                
                else:
                    player.kick('You have been banned! ({})'.format(data.get('reason')))
