#!python3

# SimPy model for an activity_injector.
# This module injects sensor data values and faults into 
# the device models at a predetermined time. 
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import simpy
import time
import json
import logging
logger = logging.getLogger(__name__)


class FaultInjector(object):
    """ 
    A FaultInjector injects faults into devices
    at specific times (by means of a SimPy interrupt).
    """
    
    def __init__(self, env):
        
        self.env = env
        
        # a dictionary of device instaces
        # <device_name>: <device_pointer>
        self.device_instances = {}
        
        # start a simpy process for the main behavior
        self.behavior_process=self.env.process(self.behavior())
        
        
    # main behavior:
    def behavior(self):
        
        # wait until some time T
        yield self.env.timeout(5)
        
        #inject faults into one device
        assert len(self.device_instances)>0
        for d in self.device_instances:
            self.device_instances[d].behavior_process.interrupt("FAULT")
            logger.info("SIM_TIME:{} FaultInjector injected a fault into device {}".format(self.env.now,d))
        # that's it.
