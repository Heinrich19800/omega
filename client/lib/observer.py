import threading
from time import time, sleep
import os
import multiprocessing

SYSTEM_LOADS = {
    'warning': 0.8,
    'danger': 1.0,
    'critical': 1.5,
    'overload': 2.0
}


class OmegaObserver(threading.Thread):
    def __init__(self, client, interval=10, duration=60*5):
        threading.Thread.__init__(self)
        
        self.system_status = {
            'level': 'normal',
            'duration': 0,
            'alerted': False
        }
        
        self.client = client
        self.interval = interval
        self.duration = duration
        self.processors = multiprocessing.cpu_count()
        self.setDaemon(True)
        self.start()
        
    def run(self):
        time_in_current_level = 0
        while True:
            time_in_current_level += 1
            current_load = os.getloadavg()[0]
            current_level = 'normal'
            for level, load in SYSTEM_LOADS.iteritems():
                load = load*self.processors
                if current_load >= load:
                    current_level = level
                    
            self.update_stats(current_level, time_in_current_level, current_load)
            sleep(self.interval)
            
    def load_level_changed(self, new_level):
        self.system_status['level'] = new_level
        self.system_status['alerted'] = False
        
    def load_alert(self, level, time_in_level, current_load):
        if not self.system_status['alerted']:
            print '[OmegaObserver] LOAD LEVEL: {} ({})'.format(level, current_load)
            self.system_status['alerted'] = True
            #TODO: Dont just print a fancy message
            # - Stop tools based on priority
            # 0 Branded
            # 1 Non-Branded
            # 2 VIP/Partner
            # 
            # - Stop in batch of 2 and redistribute if priority >= 1
            # - Contact master when stopped if due to load alert
            # - Move to backup cluster when redistributing
            # - Only redistribute if load stays for ~60 mins or exceeds critical load for ~10 mins
            #
            
            
    def update_stats(self, level, time_in_level, current_load):
        if level != self.system_status.get('level'):
            self.load_level_changed(level)
           
        if time_in_level >= self.duration:
            self.load_alert(level, time_in_level, current_load)
            
        self.system_status['duration'] = time_in_level
