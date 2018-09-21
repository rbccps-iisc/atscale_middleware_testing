#!python3

# Simpy model for a basic app.
# The app periodically obtains device data  
# from the middleware and prints all collected data.
# It also sends commands to the device.
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


# helper class for communication with the middleware
# routines for setting up entities and permissions in the middleware
sys.path.insert(0, '../messaging')
import communication_interface


class App(object):
    """ 
    An app simply polls the middleware for data at regular
    intervals and prints it. Each app has a name, and inside 
    its init function, it spawns threads to communicate 
    with the middleware.
    """
    
    def __init__(self, env, name, apikey):
        
        self.env = env
        self.name = name
        self.apikey = apikey
        
        # create a communication interface
        # to get device data from the middleware
        self.subscribe_thread = communication_interface.SubscribeInterface(
            interface_name="subscribe_thread", parent_entity_name=self.name, 
            target_entity_name=self.name, stream=None,apikey=apikey)

        # dictionary of devices being controlled by this app.
        self.controlled_devices={}
        
        # some state variables
        self.subscribe_count= 0
        self.start_real_time = 0
        self.data = [] # data obatined via subscribe requests

        # start a simpy process for the main device behavior
        self.process=self.env.process(self.behavior())
    
    def add_device_to_be_controlled(self,device_name):
        # add a device to the list of devices
        # controlled by this app over the middleware.
        # create a communication interface for this device:
        publish_thread = communication_interface.PublishInterface(
            interface_name="control_thread_"+device_name, parent_entity_name=self.name, 
            target_entity_name=device_name, stream="configure", apikey=self.apikey)
        self.controlled_devices[device_name] = publish_thread

    def send_control_message(self,device_name, msg):
        # send a command to a device through the middleware
        assert(device_name in self.controlled_devices)
        publish_thread = self.controlled_devices[device_name]
        publish_thread.queue.put(msg)
        elapsed_real_time = round(time.perf_counter() - self.start_real_time,2)
        logger.debug("SIM_TIME:{} REAL_TIME:{} ENTITY:{} sent a control message to {} message:{}".format(
            self.env.now, elapsed_real_time,self.name,device_name,msg))
  
    # main behavior of the app:
    # subscribe to data from devices, and 
    # send control messages to them
    def behavior(self):
        
        self.start_real_time = time.perf_counter()
        while True:
            
            # try to pull all accummulated messages from the queue
            count=0
            while not self.subscribe_thread.queue.empty():
                msg = self.subscribe_thread.queue.get()
                self.subscribe_count +=1
                count+=1
                self.data.append(msg)
            
            # print status msg
            elapsed_real_time = round(time.perf_counter() - self.start_real_time,2)
            logger.debug("SIM_TIME:{} REAL_TIME:{} ENTITY:{} picked up {} message(s) and has collected {} messages in total so far.".format(self.env.now, elapsed_real_time,self.name, count, self.subscribe_count))

            # now check again sometime later.
            yield self.env.timeout(1)

            # at time t=3, send a control message 
            # to all the devices controlled by this app:
            if(self.env.now == 3):
                for d in self.controlled_devices:
                    self.send_control_message(d, json.dumps({"sender": self.name, "command":"PAUSE"}))
                 
    # end the subscription thread
    # and print all data collected so far.
    def end(self):
        self.subscribe_thread.stop()
        logger.info("SIM_TIME:{} ENTITY:{} stopping. Collected {} messages in total.".format(self.env.now, self.name, self.subscribe_count))
        for msg in self.data:
            logger.debug("\t MESSAGE:{}".format(msg))


