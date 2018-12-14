#!python3

# SimPy model for a simple app.
# An app receives data published by devices 
# and sends commands to devices via the middleware.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import simpy
import json
import logging
logger = logging.getLogger(__name__)

# Interfaces for communication with the middleware
sys.path.insert(0, '../messaging')
import communication_interface

class SimpleApp(object):
	
	def __init__(self, env, ID, apikey):
		self.env = env
		self.ID = ID         # unique identifier for the app
		self.apikey = apikey # apikey required for authentication
		self.period = 0.5      # operational period for the app (in seconds)
		
		# interface for obtaining data published by devices:
		self.subscribe_thread = communication_interface.SubscribeInterface(self.ID, self.apikey)
		
		# interface for sending commands to devices:
		self.send_commands_thread = communication_interface.SendCommandsInterface(self.ID, self.apikey)
		
		# list of devices controlled by this app
		self.controlled_devices=[]
		    
		# data collected by the app
		self.device_data=[]
		
		# start a simpy process for the main app behavior
		self.behavior_process=self.env.process(self.behavior())


	def behavior(self):
		while True:
			#receive data published by devices
			if not self.subscribe_thread.queue.empty():
				while (not self.subscribe_thread.queue.empty()):
					msg = self.subscribe_thread.queue.get()
					logger.debug("SIM_TIME:{} ENTITY:{} received a message {}".format(self.env.now,self.ID, msg))
					
					if "status" in msg["data"]:
						# check if any device reported a fault.
						assert(msg["data"]["status"]=="FAULT")
						# send a resume command to the device.
						device_id = msg["sender"]
						command = json.dumps({"command":"RESUME"})
						self.send_commands_thread.send_command(device_id,command)
					else:
						# store the message
						self.device_data.append(msg)
			# now check again sometime later.
			yield self.env.timeout(self.period)
	
	# stop all communication threads
	def end(self):
		self.subscribe_thread.stop()
		self.send_commands_thread.stop()
		logger.info("SIM_TIME:{} ENTITY:{} stopping.".format(self.env.now, self.ID))
		logger.info("SIM_TIME:{} ENTITY:{} received {} messages in total".format(self.env.now,self.ID, len(self.device_data)))

