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
import visualization
import numpy as np

# helper class for communication with the middleware
# routines for setting up entities and permissions in the middleware
sys.path.insert(0, '../messaging')
import communication_interface

APP_PROTOCOL = "AMQP" # can be either "AMQP" or "HTTP"

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
        self.period = 0.5 # operational clock period for the app (in seconds)
        
        # create a communication interface
        # to get device data from the middleware
        self.subscribe_thread = communication_interface.SubscribeInterface(
            interface_name="subscribe_thread", entity_name=name, 
            apikey=apikey, exchange=str(self.name), protocol = APP_PROTOCOL)
             
        # dictionary of devices being controlled by this app.
        self.controlled_devices={}
        
        # some state variables
        self.subscribed_count= 0
        
        # create a plot for visualization of the
        # streetlights that this app is monitoring.
        self.plot=None
        
        # start a simpy process for the main device behavior
        self.process=self.env.process(self.behavior())
        
        # lists to store data from monitored devices
        self.device_ambient_light_intensity=None 
        self.device_led_light_intensity=None
        self.device_activity_detected=None
        self.device_operational_status=None
        self.device_fault_info=None
        self.device_timestamp_last_msg=None
        
        
    def initialize_streetlight_data(self):
        N = (len(self.controlled_devices))
        # initilize lists to record the latest 
        # sensor readings and state of each streetlight.
        self.device_ambient_light_intensity= [0 for i in range(N)]
        self.device_led_light_intensity= [0 for i in range(N)]
        self.device_activity_detected= [0 for i in range(N)]
        self.device_operational_status= [0 for i in range(N)]
        self.device_fault_info= [0 for i in range(N)]
        self.device_faults = [0 for i in range(N)]
        self.device_timestamp_last_msg=[0 for i in range (N)]
        
        # Initialize the plot
        self.plot = visualization.PlotStreetlights("App's View", N)
 
    def update_streetlight_data(self, msgs):
        # go through all the received messages 
        # and update the data stored about each streetlight.
        N = (len(self.controlled_devices))
        
        for m in msgs:
        
            # get the id of the sender
            dev_id = int(m["sender_id"])
            dev_name = m["sender_name"]
            assert(dev_id >=0 and dev_id<N)
            # parse the message to get data values
            self.device_ambient_light_intensity[dev_id] = float(m["ambient_light_intensity"])
            self.device_led_light_intensity[dev_id]= float(m["led_light_intensity"])
            self.device_activity_detected[dev_id] = int(m["activity_detected"])
            self.device_operational_status[dev_id] = m["operational_status"]
            self.device_fault_info[dev_id] = m["fault_info"]
            self.device_timestamp_last_msg[dev_id] = self.env.now
            
            # store the latest value of ambient light
            if (self.device_operational_status[dev_id]=="OK"):
                ambient_light = self.device_ambient_light_intensity[dev_id]
                self.device_faults[dev_id]=0
            else:
                # check if any device reported sensor faults
                # and send a "RESUME" command to this device
                self.device_faults[dev_id]=1
                logger.info("SIM_TIME:{} ENTITY:{} received a FAULT status from device {}".format(
                  self.env.now, self.name, dev_name))
                self.send_control_message(dev_name, json.dumps({"sender": self.name, "command":"RESUME"}))
        
        # check if any device hasn't communicated in a long while.
        # if so, mark it as a potential fault
        for i in range(N):
            if self.device_timestamp_last_msg[i] < (self.env.now-5):
                self.device_faults[i]=1 # this light is probably faulty
                self.device_led_light_intensity[i]=0
                self.device_activity_detected[i]=0
            
        # update the plot for streetlight data  
        self.plot.update_plot(intensities=self.device_led_light_intensity, 
            activities=self.device_activity_detected, faults= self.device_faults, 
            ambient_light_level=ambient_light)

    # main behavior of the app:
    # subscribe to data from devices, and 
    # send control messages to them
    def behavior(self):
        self.initialize_streetlight_data() 
        while True:
            
            # try to pull all accummulated messages from the queue
            msgs = self.get_unread_messages()
            if(msgs!=None):
                
                logger.debug("SIM_TIME:{} ENTITY:{} picked up {} message(s) and has collected {} "
                "messages in total so far.".format(self.env.now, self.name, len(msgs), self.subscribed_count))
                
                # infer the state of the streetlights from the
                # received messages and produce a visualization
                self.update_streetlight_data(msgs)

                                    
            # now check again sometime later.
            yield self.env.timeout(self.period)

            # at time t=3, send a dummy control message 
            # to all the devices controlled by this app:
            if(self.env.now == 3):
                for d in self.controlled_devices:
                    self.send_control_message(d, json.dumps({"sender": self.name, "command":"DUMMY_COMMAND"}))


    def add_device_to_be_controlled(self,device_name):
        # add a device to the list of devices
        # controlled by this app over the middleware.
        # create a communication interface for this device:
        publish_thread = communication_interface.PublishInterface(
            interface_name="control_thread_"+device_name, entity_name=self.name, 
            apikey=self.apikey, exchange=str(device_name)+".configure", protocol=APP_PROTOCOL)
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


