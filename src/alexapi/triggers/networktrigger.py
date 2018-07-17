import threading
import logging
from socket import AF_INET, socket, SOCK_STREAM
import select
import json

import alexapi.triggers as triggers
from .basetrigger import BaseTrigger

logger = logging.getLogger(__name__)


class NetworkTrigger(BaseTrigger):

	type = triggers.TYPES.OTHER
	buffer_size = 1024
	
	def __init__(self, config, trigger_callback):
		super(NetworkTrigger, self).__init__(config, trigger_callback, 'network')
		
		self._enabled_lock = threading.Event()
		# self._disabled_lock = threading.Event()
		
		self._host = ''
		self._port = self._tconfig['port']
		self._server = None

	def setup(self):
		self._server = socket(AF_INET, SOCK_STREAM)
		self._server.bind((self._host, self._port))
		
	def run(self):
		self._server.listen(self._tconfig['num_network_triggers'])
		
		thread = threading.Thread(target=self.thread, args=())
		thread.daemon = True
		thread.start()

	def thread(self):
		while True:
			client, client_address = self._server.accept()
			client_thread = threading.Thread(target=self.handle_client, args=(client,))
			client_thread.daemon = True
			client_thread.start()
			
	def handle_client(self, client):
		
		message_header = {}
		message_body = {}
		msg = {'message_header': message_header, 'message_body': message_body}
		
		if self._enabled_lock.is_set():
			triggered = False
			while not triggered:
				# See if the socket is marked as having data ready.
				ready_to_read, ready_to_write, in_error = select.select((client,), [], [], 0)
				
				if ready_to_read:
					j = json.loads(client.recv(NetworkTrigger.buffer_size))
					
					# Client cancelled the connection
					if len(j) == 0:
						break
					
					msg_header = j['message_header']
					# msg_body = j['message_body']
					
					if msg_header['type'] == TriggerMessages.TRIGGER:
						triggered = True
					elif msg_header['type'] == TriggerMessages.OTHER:
						pass
					
			if triggered:
				# self._disabled_lock.set()
				self._trigger_callback(self)
				message_header['is_successful'] = Status.SUCCESS
		else:
			message_header['is_successful'] = Status.FAIL
			
		client.send(json.dumps(msg))
		client.close()
			
	def enable(self):
		self._enabled_lock.set()
		# self._disabled_lock.clear()

	def disable(self):
		self._enabled_lock.clear()
		# self._disabled_lock.wait()
		
		
class TriggerMessages(object):
	TRIGGER = 'trigger'
	OTHER = 'other'
	
class Status(object):
	SUCCESS = 'success'
	FAIL = 'fail'
