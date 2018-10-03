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
        self.period = 1 # operational clock period for the app (in seconds)
        
        # create a communication interface
        # to get device data from the middleware
        self.subscribe_thread = communication_interface.SubscribeInterface(
            interface_name="subscribe_thread", parent_entity_name=self.name, 
            target_entity_name=self.name, stream=None,apikey=apikey)
             
        # dictionary of devices being controlled by this app.
        self.controlled_devices={}
        
        # some state variables
        self.subscribed_count= 0
        self.received_messages = [] # data obatined via subscribe requests

        # start a simpy process for the main device behavior
        self.process=self.env.process(self.behavior())
    
    
    # main behavior of the app:
    # subscribe to data from devices, and 
    # send control messages to them
    def behavior(self):
        
        while True:
            
            # try to pull all accummulated messages from the queue
            msgs = self.get_unread_messages()
            if(msgs!=None):
                self.received_messages.extend(msgs)
                logger.debug("SIM_TIME:{} ENTITY:{} picked up {} message(s) and has collected {} messages in total so far.".format(self.env.now, self.name, len(msgs), self.subscribed_count))

                # check if any device sent a "FAULT" status
                for m in msgs:
                    if "status" in m["data"]:
                        assert(m["data"]["status"]=="FAULT")
                        # check who sent this message
                        device = m["data"]["sender"]
                        # send a "RESUME" command to this device
                        logger.info("SIM_TIME:{} ENTITY:{} received a FAULT status from device {}".format(
                            self.env.now, self.name, device))
                        self.send_control_message(device, json.dumps({"sender": self.name, "command":"RESUME"}))
                
            # now check again sometime later.
            yield self.env.timeout(self.period)

            # at time t=3, send a dummy control message 
            # to all the devices controlled by this app:
            #if(self.env.now == 3):
            #    for d in self.controlled_devices:
            #        self.send_control_message(d, json.dumps({"sender": self.name, "command":"DUMMY_COMMAND"}))


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
        logger.debug("SIM_TIME:{} ENTITY:{} sent a control message to {}, message:{}".format(
            self.env.now, self.name,device_name,msg))
             
    # get unread messages from the
    # subscribe queue.
    def get_unread_messages(self):
        unread_messages=[]
        if self.subscribe_thread.queue.empty():
            return None
        else:
            while not self.subscribe_thread.queue.empty():
                msg = self.subscribe_thread.queue.get()
                self.subscribed_count +=1
                unread_messages.append(msg)
            return unread_messages 

    # IMPORTANT! :
    # stop all communication threads
    # for a proper cleanup.
    def end(self):
        self.subscribe_thread.stop()
        for d in self.controlled_devices:
            publish_thread = self.controlled_devices[d]
            publish_thread.stop()
        logger.info("SIM_TIME:{} ENTITY:{} stopping. Collected {} messages in total.".format(self.env.now, self.name, self.subscribed_count))
        for msg in self.received_messages:
            logger.debug("\t MESSAGE:{}".format(msg))


