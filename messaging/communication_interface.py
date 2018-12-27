# !python3 
#
# Interface classes used by device/app entities
# for performing non-blocking communication with the middleware.
# A device/app entity can spawn multiple communication 
# interfaces. Each interface runs as an independent thread. 
# The threads communicate with the parent entity via queues.
#
# There are four basic interface types:
#		
#		1. PublishInterface: used by a device for publishing data
#		2. SendCommandsInterface: used by an app for sending commands to devices
#		3. SubscribeInterface: used by an app for receiving data
#		4. ReceiveCommandsInterface: used by a device for receiving commands from an app
#	
#		For the Subscribe and ReceiveCommands interfaces, 
#		two versions are available: POLLING and CALL-BACK.
#		The CALL-BACK versions are more responsive and recommended.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import json
import logging
logger = logging.getLogger(__name__)
import pika

# routines for communicating with the corinthian middleware
import corinthian_messaging
from corinthian_messaging import Corinthian_ip_address, Corinthian_port


class PublishInterface(object):
	""" Interface used by a device for publishing data to the middleware."""
	def __init__(self, ID, apikey):
		self.ID = ID
		self.apikey = apikey
		
		# create a queue to communicate with the parent entity
		self.queue = Queue()
		
		# count of the messages published
		self.count =0
	
		# open a channel in pika
		credentials = pika.PlainCredentials(self.ID, self.apikey)
		parameters = pika.ConnectionParameters(Corinthian_ip_address, Corinthian_port, '/', credentials, ssl=True)
		connection = pika.BlockingConnection(parameters)
		self.channel = connection.channel()

		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.debug("PublishInterface thread created with ID={}.".format(self.ID))

	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.debug("PublishInterface thread with ID={} was stopped.".format(self.ID))
		self.channel.close()
	    
	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
	
	# routine used by a device for inserting a 
	# message into the publish queue.
	def publish(self,data):
		self.queue.put(data)
	
	# main behavior
	def behavior(self):
		while not self.stopped():
			# wait until there's a msg to be published
			data = self.queue.get()
			# send the message to the middleware
			#corinthian_messaging.publish(self.ID, self.apikey, self.ID, "#", "protected", data)
			success = self.channel.basic_publish(exchange=self.ID+".protected", properties=pika.BasicProperties(user_id=self.ID), 
				routing_key="<unspecified>", body=str(data))
			if success:
				logger.debug("PublishInterface thread with ID={} published data={}".format(self.ID, data))
			else:
				logger.error("PublishInterface thread with ID={} FAILED to publish data={}".format(self.ID, data))
			self.count +=1
        

class SubscribeInterface(object):
	""" Interface used by an app for obtaining data 
	from the middleware. Uses a call-back instead of polling.
	The pika library calls a specified call-back function
	whenever a message arrives for the consumer.
	"""
	# The call-back function
	def callback(self, ch, method, properties, body):
		self.count+=1
		data = json.loads(body.decode('utf-8'))
		sender = properties.user_id
		logger.debug("SubscribeInterface thread with ID={} received a message: {} from {}".format(self.ID,data,sender))
		msg={"data":data,"sender":sender}
		# push the message into the queue
		self.queue.put(msg)

	def __init__(self, ID, apikey):
		
		self.ID = ID
		self.apikey = apikey

		# create a queue to communicate with the parent entity
		self.queue = Queue()
		
		# count of the messages received
		self.count =0
		
		# open a channel in pika
		credentials = pika.PlainCredentials(self.ID, self.apikey)
		parameters = pika.ConnectionParameters(Corinthian_ip_address, Corinthian_port, '/', credentials, ssl=True)
		connection = pika.BlockingConnection(parameters)
		self.channel = connection.channel()
		
		# register the call-back with middleware
		self.channel.basic_consume(self.callback, queue=self.ID, no_ack=True)
		
		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.debug("SubscribeInterface thread created with ID={}.".format(self.ID))
		   
	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		self.channel.stop_consuming()
		logger.debug("SubscribeInterface thread with ID={} was stopped.".format(self.ID))
	    
	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
		
	def behavior(self):
		if not self.stopped():
			self.channel.start_consuming()
		

class SendCommandsInterface(object):
	""" Interface used by an app for sending commands to a device via the middleware."""
	def __init__(self, ID, apikey):
		self.ID = ID
		self.apikey = apikey
		
		# create a queue.
		# The parent entity (app) pushes commands into this queue
		# which are then picked up by the SendCommands thread
		# and sent to the middleware.
		self.queue = Queue()
		
		# count of the commands sent
		self.count =0
		
		# open a channel in pika
		credentials = pika.PlainCredentials(self.ID, self.apikey)
		parameters = pika.ConnectionParameters(Corinthian_ip_address, Corinthian_port, '/', credentials, ssl=True)
		connection = pika.BlockingConnection(parameters)
		self.channel = connection.channel()

		
		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.debug("SendCommandsInterface thread created with ID={}.".format(self.ID))

	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.debug("SendCommandsInterface thread with ID={} was stopped.".format(self.ID))
		self.channel.close()
	    
	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
	
	# routine used by an app for sending a 
	# command to a specified device.
	def send_command(self,device_id,command):
		cmd = {"device_id":str(device_id), "command":str(command)}
		self.queue.put(cmd)
	
	# main behavior
	def behavior(self):
		while not self.stopped():
			# wait until there's a msg to be published
			cmd = self.queue.get()
			device_id = cmd["device_id"]
			command = cmd["command"]
			
			# send a command to the device via the middleware
			#corinthian_messaging.publish(ID=self.ID, apikey=self.apikey, to=device_id, topic="#", message_type="command", data=command)
			success = self.channel.basic_publish(exchange=self.ID+".publish", properties=pika.BasicProperties(user_id=self.ID),
				routing_key=device_id+".command.#", body=str(command))
			if success:
				logger.debug("SendCommandsInterface thread with ID={} sent a command={} to device={}".format(self.ID, command, device_id))
			else:
				logger.debug("SendCommandsInterface thread with ID={} FAILED to send a command={} to device={}".format(self.ID, command, device_id))
			self.count +=1

class ReceiveCommandsInterface(object):
	""" Interface used by a device for receiving commands.
	Uses a call-back instead of polling.
	"""
	# The call-back function
	def callback(self, ch, method, properties, body):
		self.count+=1
		command = json.loads(body.decode('utf-8'))
		sender = properties.user_id
		logger.debug("ReceiveCommandsInterface thread with ID={} received a command {} from {}".format(self.ID, command, sender))
		msg={"data":command,"sender":sender}
		# push the message into the queue
		self.queue.put(msg)

	def __init__(self, ID, apikey):
		
		self.ID = ID
		self.apikey = apikey

		# create a queue to communicate with the parent entity
		self.queue = Queue()
		
		# count of the messages received
		self.count =0
		
		# open a channel in pika
		credentials = pika.PlainCredentials(self.ID, self.apikey)
		parameters = pika.ConnectionParameters(Corinthian_ip_address, Corinthian_port, '/', credentials, ssl=True)
		connection = pika.BlockingConnection(parameters)
		self.channel = connection.channel()
		
		# register the call-back with middleware
		self.channel.basic_consume(self.callback, queue=self.ID+".command", no_ack=True)

		
		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.debug("ReceiveCommandsInterface thread created with ID={}.".format(self.ID))
		   
	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		self.channel.stop_consuming()
		logger.debug("ReceiveCommandsInterface thread with ID={} was stopped.".format(self.ID))

	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
		
	def behavior(self):
		if not self.stopped():
			self.channel.start_consuming()

#=============================
# Polling-based interfaces...
# these are less responsive than their
# non-polling counterparts.
#=================================

class SubscribeInterfacePolling(object):
	""" Polling-based Interface used by an app for obtaining data from the middleware."""
	
	def __init__(self, ID, apikey):
		
		self.ID = ID
		self.apikey = apikey

		# Polling interval in seconds
		self.polling_interval=1
		
		# create a queue to communicate with the parent entity
		self.queue = Queue()
		
		# count of the messages received
		self.count =0
		
		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.debug("SubscribeInterfacePolling thread created with ID={}.".format(self.ID))
		   
	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.debug("SubscribeInterfacePolling thread with ID={} was stopped.".format(self.ID))
	    
	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
		
	def behavior(self):
		while not self.stop_event.wait(timeout=self.polling_interval):
			messages = corinthian_messaging.subscribe(ID=self.ID, apikey=self.apikey,num_messages=100)
			for m in messages.json():
				data = m["body"]
				sender = m["sent-by"]
				logger.debug("SubscribeInterfacePolling thread with ID={} received a message: {} from {}".format(self.ID,data,sender))
				msg={"data":data,"sender":sender}
				# push the message into the queue
				self.queue.put(msg)
				self.count += 1

class ReceiveCommandsInterfacePolling(object):
	""" Polling-based Interface used by a device for receiving commands."""
	
	def __init__(self, ID, apikey):
		
		self.ID = ID
		self.apikey = apikey

		# Polling interval in seconds
		self.polling_interval=1
		
		# create a queue to communicate with the parent entity
		self.queue = Queue()
		
		# count of the messages received
		self.count =0
		
		
		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.debug("ReceiveCommandsInterfacePolling thread created with ID={}.".format(self.ID))
		   
	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.debug("ReceiveCommandsInterfacePolling thread with ID={} was stopped.".format(self.ID))
	    
	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
		
		
	def behavior(self):
		while not self.stop_event.wait(timeout=self.polling_interval):
			messages = corinthian_messaging.subscribe(ID=self.ID, apikey=self.apikey, message_type="command",num_messages=100)
			for m in messages.json():
				logger.debug("ReceiveCommandsInterfacePolling thread with ID={} received a command {}".format(self.ID, m))
				command = m["body"]
				sender = m["sent-by"]
				logger.debug("ReceiveCommandsInterfacePolling thread with ID={} received a command {} from {}".format(self.ID, command, sender))

				msg={"command":data,"sender":sender}
				# push the command into the queue
				self.queue.put(msg)
				self.count += 1





#======================================
# Testbench
#======================================
import setup_entities
import time

if __name__=='__main__':
    
	# logging settings:
	logging.basicConfig(level=logging.DEBUG)
	# suppress debug messages from other modules used.
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("pika").setLevel(logging.WARNING)
	logging.getLogger("corinthian_messaging").setLevel(logging.WARNING)
	logging.getLogger("setup_entities").setLevel(logging.INFO)
	

	devices = ["device1"]
	apps = ["app1"]
	
	system_description = {  "devices" : devices,
	                        "apps": apps,
	                        "permissions" : [(a,d,"read-write") for a in apps for d in devices]
	                    }
	registered_entities = []
	 
	# register a device and an app and set up permissions
	success, registered_entities = setup_entities.register_entities(system_description)
	
	# create interface threads for each device
	p=[]  # publish threads
	rc=[] # receive commands threads
	s=[]  # subscribe threads
	sc=[] # send command threads

	for d in devices:
		p.append(PublishInterface("admin/"+d,registered_entities["admin/"+d]))
		rc.append(ReceiveCommandsInterface("admin/"+d,registered_entities["admin/"+d]))

	for a in apps:
		s.append(SubscribeInterface("admin/"+a,registered_entities["admin/"+a]))
		sc.append(SendCommandsInterface("admin/"+a,registered_entities["admin/"+a]))
	
	try:
		# push something into the publish and command queues for each device
		for i in range (10):
			data = json.dumps({"sensor_value":str(i),"type":"A"})
			print("\nPublishing data:",data)
			
			# push something into the publish queue
			for j in range(len(devices)):
				p[j].publish(data)
			
			# push something into the commands queue
			for a in range(len(apps)):
				for d in range(len(devices)):
					sc[a].send_command(device_id="admin/"+devices[d],command=json.dumps({"command":"DUMMY_COMMAND_"+str(i)}))
			time.sleep(1)
		
		
		# delay
		time.sleep(2)
	
		for j in range(len(apps)):
			# pull messages from the subscribe queues
			print("\nThe following messages were present in the subscribe queue for ",apps[j])
			while(not s[j].queue.empty()):
				msg = s[j].queue.get()
				print(msg)

		# pull messages from the device's commands queues
		for d in range(len(devices)):
			print("\nThe following messages were present in the commands queue for ",devices[d])
			while(not rc[d].queue.empty()):
				msg = rc[d].queue.get()
				print(msg)
		print("\n")

	except:
		raise
	finally:
		for i in range(len(devices)):
			#stop all child threads
			p[i].stop()
			rc[i].stop()
		for j in range(len(apps)):
			s[j].stop()
			sc[j].stop()
		print("De-registering all entities")
		setup_entities.deregister_entities(registered_entities)

