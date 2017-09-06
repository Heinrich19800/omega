from time import sleep, time
import threading

BASE_INTERVAL = 1


class Scheduler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.active = True
        self.setDaemon(True)
        
        self.queue = {}
        self.killed_tasks = []
        self._id = 0
        
        self.last = time()
        self.start()
        
    def add_task(self, function, execute_time, repeating=False, **params):
        task_id = str(self._id)
        self.queue[task_id] = {
            "execute_time": execute_time,
            "repeating": repeating,
            "function": function,
            "params": params
        }
        self._id += 1
        return task_id
        
    def remove_task(self, task_id):
        self.killed_tasks.append(task_id)
        
    def execute(self, task, timestamp):
        task.get('function')(**task.get('params'))
        if not task.get('repeating'):
            return True
            
        else:
            return {
                'function': task.get('function'),
                'params': task.get('params'),
                'execute_time': timestamp + task.get('repeating'),
                'repeating': task.get('repeating')
            }
        
    def stop(self):
        self.active = False

    def run(self):
        finished_tasks = []
        while self.active:
            finished_tasks = []
            timestamp = time()
            for task_id, task in dict(self.queue).iteritems():
                if timestamp >= task.get('execute_time'):
                    result = self.execute(task, timestamp)
                    if result == True:
                        finished_tasks.append(task_id)
                        
                    else:
                        self.queue[task_id] = result
                        
            for task_id in finished_tasks:
                del self.queue[task_id]
                
            for task_id in list(self.killed_tasks):
                del self.queue[task_id]
                self.killed_tasks.remove(task_id)
            
            self.last = time()
            sleeptime = BASE_INTERVAL - (self.last - timestamp)
            sleep(sleeptime if sleeptime > 0 else BASE_INTERVAL)
