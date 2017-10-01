import threading


class Callback(object):
    def verify_existance(self, endpoint, action):
        if not hasattr(self, '_callbacks'):
            return False
            
        if endpoint not in self._callbacks:
            return False
    
        if action not in self._callbacks[endpoint]:
            return False
            
        return True
    
    def create_callback(self, endpoint, action):
        if not hasattr(self, '_callbacks'):
            self._callbacks = {}
            
        if endpoint not in self._callbacks:
            self._callbacks[endpoint] = {}

        if action not in self._callbacks[endpoint]:
            self._callbacks[endpoint][action] = []
        
    def create_callbacks(self, endpoint, actions):
        if not hasattr(self, '_callbacks'):
            self._callbacks = {}
            
        if endpoint not in self._callbacks:
            self._callbacks[endpoint] = {}

        for action in actions:
            if action not in self._callbacks[endpoint]:
                self._callbacks[endpoint][action] = []
        
    def register_callback(self, endpoint, action, method_reference):
        self.create_callback(endpoint, action)
        self._callbacks[endpoint][action].append(method_reference)
        
    def async_trigger_callback(self, endpoint, action, data={}):
        threading.Thread(target=self.trigger_callback, args=[endpoint, action, data]).start()
        
    def trigger_callback(self, endpoint, action, data={}):
        if not self.verify_existance(endpoint, action):
            print 'Error while executing callback: {}-{}: non existent'.format(endpoint, action)
            
        for method in self._callbacks.get(endpoint).get(action):
            method(data)
