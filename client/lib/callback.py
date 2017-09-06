

class Callback(object):
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

    def trigger_callback(self, endpoint, action, data={}):
        try:
            for method in self._callbacks.get(endpoint).get(action):
                method(data)
        
        except Exception as e: #TODO: remove at some point
            print 'Error while executing callback: {}-{}: {}'.format(endpoint, action, e)
            raise
