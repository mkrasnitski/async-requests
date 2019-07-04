import ctypes
import time
import sys
import threading
import requests
from queue import Queue

q = Queue()
responses = []
percent_milestone = 1
lock = threading.Lock()

class thread_with_exception(threading.Thread): 
	def __init__(self, *args, **kwargs): 
		threading.Thread.__init__(self, *args, **kwargs) 

	def get_id(self): 
		# returns id of the respective thread 
		if hasattr(self, '_thread_id'): 
			return self._thread_id 
		for id, thread in threading._active.items(): 
			if thread is self: 
				return id

	def raise_exception(self): 
		thread_id = self.get_id() 
		res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit)) 
		if res > 1: 
			ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0) 
			print('Exception raise failure') 

def worker():
	while True:
		args = q.get()
		if args is None:
			break
		get_response(*args)
		q.task_done()

def get_response(url, headers, i, verbose):
	try:
		responses[i] = requests.get(url, headers=headers, timeout=1000)
		# print(responses[i])`
	except Exception as e:
		print(e)

	if verbose == 1:
		with lock:
			global percent_milestone
			numerator = len(responses) - responses.count(None)
			denominator = len(responses)
			bar = '='*(percent_milestone-1)
			tail = '.'*(25-percent_milestone)
			print(str(numerator).rjust(len(str(denominator))) + f"/{denominator} [{bar}>{tail}]", end='\r', flush=True)
			percent_complete = int(100*numerator/denominator)
			if percent_complete // 4 >= percent_milestone:
				percent_milestone += 1
			if percent_complete == 100:
				print(str(numerator).rjust(len(str(denominator))) + f'/{denominator} [' + '='*25 + ']')

def async_get(urls, headers=None, num_workers=100, verbose=1):
	global q
	global responses
	global percent_milestone
	q = Queue(len(urls))
	responses = [None]*len(urls)
	percent_milestone = 1
	threads = []
	for i in range(num_workers):
		t = thread_with_exception(target=worker)
		t.daemon = True
		t.start()
		threads.append(t)

	for i, url in enumerate(urls):
		q.put((url, headers, i, verbose))

	try:
		while not q.empty():
			time.sleep(0.1)
	except KeyboardInterrupt:
		for t in threads:
			t.raise_exception()
		print('KeyboardInterrupt')
		sys.exit()
	finally:
		for i in range(num_workers):
			q.put(None)
		for t in threads:
			t.join()
	return responses