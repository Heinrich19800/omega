class OmegaClientError(Exception):
    pass

class OmegaAuthenticationError(Exception):
    pass

class OmegaAPIError(Exception):
    pass

class OmegaWorkerError(Exception):
    errors = {}
    message = ''
    
    def __init__(self, server_id, message):
        self.message = ' - Exception in worker {}: {}'.format(server_id, message)
    
        if server_id not in self.errors:
            self.errors[server_id] = []
            
        self.errors[server_id].append(message)
        
        
    def __str__(self):
        print self.message

class BattleEyeRconError(Exception):
    pass