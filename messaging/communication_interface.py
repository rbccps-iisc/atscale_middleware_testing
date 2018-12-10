# !python3 
#
# Interface classes for performing non-blocking communication with the middleware.
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
	""" Interface used by an app for obtaining data from the middleware."""
	
	def __init__(self, ID, apikey):
		
		self.ID = ID
		self.apikey = apikey
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
	
	devices = ["device1", "device2"]
	apps =  ["application1","application2"]
	
	system_description = {  "entities" : devices+apps,
	                        "permissions" : [(a,d,"read-write") for a in apps for d in devices]
	                    }
	registered_entities = []
	 
	# register a device and an app and set up permissions
	try:
		success, registered_entities = setup_entities.setup_entities(system_description)
	except:
		print("---------------------")
		print("De-registering all entities")
		entities=[ "admin/"+str(i) for i in devices] + ["admin/"+str(i) for i in apps]
		setup_entities.deregister_entities(entities)
		print("---------------------")
		raise
	
	assert(success)
	# create publish threads for "device1" and "device2"
	p1 = PublishInterface("admin/device1",registered_entities["admin/device1"])
	p2 = PublishInterface("admin/device2",registered_entities["admin/device2"])
	
	# create subscribe threads for "application1" and "application2"
	s1 = SubscribeInterface("admin/application1",registered_entities["admin/application1"])
	s2 = SubscribeInterface("admin/application2",registered_entities["admin/application2"])
	
	try:
		# push something into each of the publish queues
		NUM_MSG = 10
		for i in range (NUM_MSG):
			p1.publish(json.dumps({"value":str(i), "type":"A"}))
			p2.publish(json.dumps({"value":str(i), "type":"B"}))
		time.sleep(2)
	
		# pull messages from the subscribe queues
		print("The following messages were present in the subscribe queue for application1:")
		while(not s1.queue.empty()):
			msg = s1.queue.get()
			print(msg)
		
		print("The following messages were present in the subscribe queue for application2:")
		while(not s2.queue.empty()):
			msg = s2.queue.get()
			print(msg)
	except:
		raise
	finally:
		#stop all child threads
		p1.stop()
		p2.stop()
		s1.stop()
		s2.stop()
		print("---------------------")
		print("De-registering all entities")
		setup_entities.deregister_entities(registered_entities)
		print("---------------------")

