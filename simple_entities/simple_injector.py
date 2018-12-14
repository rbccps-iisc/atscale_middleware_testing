#!python3

# SimPy model for an injector module.
# The injector module injects faults into devices
# at a predetermined time (via a SimPy interrupt).
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


class SimpleInjector(object):
	
	def __init__(self, env, name):
		self.env = env
		self.name = name     # name of the fault injector
		
		# a dictionary of device instaces
		# to be interrupted.
		# <device_name>: <device_pointer>
		self.device_instances = {}
		
		# start a simpy process for the main behavior
		self.behavior_process=self.env.process(self.behavior())

	 # main behavior:
	def behavior(self):
	    
		# wait until some time T
		yield self.env.timeout(5)
		
		#inject faults into all devices
		assert len(self.device_instances)>0
		for d in self.device_instances:
			self.device_instances[d].behavior_process.interrupt("FAULT")
			logger.info("SIM_TIME:{} SimpleInjector {} injected a fault into device {}".format(self.env.now, self.name, d))
		# that's it.
