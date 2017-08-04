import time
import datetime
import threading

MODULE_NAME = 'RestartScheduler'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_restartscheduler'

#TODO: Multiple restarts

DEFAULT_CONFIG = {
    'active': False,
    'restart_at': '04:00', #24 Hour format
    'send_warning': True
}

class RestartScheduler(threading.Thread):
    def __init__(self, worker):
        threading.Thread.__init__(self)
        self.config = DEFAULT_CONFIG
        self._worker = worker

        config = self._worker.get_module_config(MODULE_CONFIG_ID)
        if config:
            self.config = config
        
        if not self.config.get('active'):
            return

        self._parse_time()
        
        parsed_time = datetime.datetime.strptime(self.config.get('restart_at'), '%H:%M')
        self.config['restart_at'] = {
            'hour': parsed_time.hour,
            'minute': parsed_time.minute
        }
        
        self.start()
        
    def _invoke_server_restart(self):
        self._worker._rcon.restart_server()
        self._worker.stop(wait=False, timeout=60, reason='invoked_server_restart')
        self._worker._client._worker_reinitiate(self._worker.server_id, 'invoked_server_restart')
    
    def _check_for_restart(self):
        if self.current_hour == self.config.get('restart_at').get('hour') and \
        self.current_minute == self.config.get('restart_at').get('minute'):
            return True
            
        return False
        
    def _check_for_warning(self):
        if self.current_hour == self.config.get('restart_at').get('hour') and \
        self.current_minute == self.config.get('restart_at').get('minute')-5:
            return True
            
        return False
        
    def _parse_time(self):
        parsed_time = datetime.datetime.strptime(time.strftime('%H:%M:%S'), '%H:%M:%S')
        self.current_hour =  parsed_time.hour
        self.current_minute = parsed_time.minute
    
    def run(self):
        while self._worker._active:
            self._parse_time()
            
            if self._check_for_warning():
                self._worker._rcon.say_all('[Scheduled Restart] The server will restart in 5 minutes!')
            
            if self._check_for_restart():
                self._invoke_server_restart()
                
            time.sleep(30)
        
def hook():
    return [MODULE_NAME, MODULE_AUTHOR, RestartScheduler]