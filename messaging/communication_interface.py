# !python3 
#
# Interface classes used by device/app entities
# for performing non-blocking communication with the middleware.
# There are four basic interfaces:
#		PublishInterface: used by a device for publishing data
#		SubscribeInterface: used by an app for receiving data
#		SendCommandsInterface: used by an app for sending commands to devices
#		ReceiveCommandsInterface: used by a device for receiving commands from an app
#
# A device/app entity can spawn multiple communication 
# interfaces. Each interface runs as an independent thread. 
# The threads communicate with the parent entity via queues.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import json
import logging
logger = logging.getLogger(__name__)

# routines for communicating with the corinthian middleware
import corinthian_messaging


class PublishInterface(object):
	""" Interface used by a device for publishing data to the middleware."""
	def __init__(self, ID, apikey):
		self.ID = ID
		self.apikey = apikey
		
		# create a queue to communicate with the parent entity
		self.queue = Queue()
		
		# count of the messages published
		self.count =0
		
		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.info("PublishInterface thread created with ID={}.".format(self.ID))

	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.info("PublishInterface thread with ID={} was stopped.".format(self.ID))
	    
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
			corinthian_messaging.publish(self.ID, self.apikey, self.ID, "#", "protected", data)
			logger.debug("PublishInterface thread with ID={} published data={}".format(self.ID, data))
			self.count +=1
		return
        


class SubscribeInterface(object):
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
		logger.info("SubscribeInterface thread created with ID={}.".format(self.ID))
		   
	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.info("SubscribeInterface thread with ID={} was stopped.".format(self.ID))
	    
	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
		
		
	def behavior(self):
		while not self.stop_event.wait(timeout=self.polling_interval):
			messages = corinthian_messaging.subscribe(ID=self.ID, apikey=self.apikey,num_messages=100)
			for m in messages.json():
				logger.debug("SubscribeInterface thread with ID={} received a message: {}".format(self.ID, m))
				# push the message into the queue
				self.queue.put(m)
				self.count += 1


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
		
		# spawn the behaviour function as an independent thread
		self.stop_event = threading.Event()
		self.thread = threading.Thread(target=self.behavior)
		self.thread.daemon = True
		self.thread.start()
		logger.info("SendCommandsInterface thread created with ID={}.".format(self.ID))

	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.info("SendCommandsInterface thread with ID={} was stopped.".format(self.ID))
	    
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
			corinthian_messaging.publish(ID=self.ID, apikey=self.apikey, to=device_id, topic="#", message_type="command", data=command)
			logger.debug("SendCommandsInterface thread with ID={} sent a command={} to device={}".format(self.ID, command, device_id))
			self.count +=1
		return

class ReceiveCommandsInterface(object):
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
		logger.info("ReceiveCommandsInterface thread created with ID={}.".format(self.ID))
		   
	# a function to stop the thread from outside
	def stop(self):
		self.stop_event.set()
		logger.info("ReceiveCommandsInterface thread with ID={} was stopped.".format(self.ID))
	    
	# check if the thread was stopped.
	def stopped(self):
		return self.stop_event.is_set()
		
		
	def behavior(self):
		while not self.stop_event.wait(timeout=self.polling_interval):
			messages = corinthian_messaging.subscribe(ID=self.ID, apikey=self.apikey, message_type="command",num_messages=100)
			for m in messages.json():
				logger.debug("ReceiveCommandsInterface thread with ID={} received a message: {}".format(self.ID, m))
				# push the message into the queue
				self.queue.put(m)
				self.count += 1


#------------------------------------
# Testbench
#------------------------------------
import setup_entities
import time

if __name__=='__main__':
    
	# logging settings:
	logging.basicConfig(level=logging.INFO)
	# suppress debug messages from other modules used.
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("pika").setLevel(logging.WARNING)
	logging.getLogger("setup_entities").setLevel(logging.INFO)
	
	devices = ["device1"]
	apps =  ["application1"]
	
	system_description = {  "devices" : devices,
							"apps": apps,
	                        "permissions" : [(a,d,"read-write") for a in apps for d in devices]
	                    }
	registered_entities = []
	 
	# register a device and an app and set up permissions
	success, registered_entities = setup_entities.register_entities(system_description)
	
	# create interface threads for device1 
	p = PublishInterface("admin/device1",registered_entities["admin/device1"])
	rc = ReceiveCommandsInterface("admin/device1",registered_entities["admin/device1"])

	# create interface threads for app1 
	s = SubscribeInterface("admin/application1",registered_entities["admin/application1"])
	sc = SendCommandsInterface("admin/application1",registered_entities["admin/application1"])
	
	try:
		# push something into the publish queue
		for i in range (10):
			#p.publish(json.dumps({"value":str(i), "type":"A"}))
			p.publish("DUMMY_DATA_"+str(i))
		
		# push something into the commands queue
		sc.send_command(device_id="admin/device1",command="DUMMY_COMMAND")
	
		# delay	
		time.sleep(3)

		# pull messages from the subscribe queues
		print("\nThe following messages were present in the subscribe queue for application1:")
		while(not s.queue.empty()):
			msg = s.queue.get()
			print(msg)
		# pull messages from the device's commands queue
		print("\nThe following messages were present in the commands queue for device1:")
		while(not rc.queue.empty()):
			msg = rc.queue.get()
			print(msg)
		print("\n")

	except:
		raise
	finally:
		#stop all child threads
		p.stop()
		s.stop()
		sc.stop()
		rc.stop()
		print("De-registering all entities")
		setup_entities.deregister_entities(registered_entities)

