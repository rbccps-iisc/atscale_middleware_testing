#!/usr/bin/env python3

# Simpy model for a basic device
# The device simply publishes data
# to the middleware at regular intervals.
#
#
# Author: Neha Karanjkar

#!python3
from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import simpy
import time
import json


# helper class for communication with the middleware
# routines for setting up entities and permissions in the middleware
sys.path.insert(0, '../messaging')
import communication_interface
from communication_interface import print_lock 

class Device(object):
    """ A device simply publishes data to the 
    middleware at regular intervals.
    Each device has a name, and inside its init function,
    it spawns some threads to communicate with the middleware.
    """
    
    def __init__(self, env, name, apikey):
        
        self.env = env
        self.name = name
        
        # create a communication interface
        self.publish_thread = communication_interface.PublishInterface("publish_thread", self.name, self.name, "protected", apikey)
        self.publish_thread.verbose=False

        # create an interface to receive control messages
        self.subscribe_thread = communication_interface.SubscribeInterface("subscribe_thread", self.name, self.name, "configure", apikey)
        self.subscribe_thread.verbose=True

        # some state variables
        self.published_count= 0
        self.start_real_time = 0

        # start a simpy process for the main device behavior
        self.process=self.env.process(self.behavior())
    
    
    # helper routine to publish a message
    def publish(self,msg):
        self.publish_thread.queue.put(msg)
        self.published_count +=1
        elapsed_real_time = round(time.perf_counter() - self.start_real_time,2)
        with print_lock:
            print("SIM TIME =",self.env.now, "REAL TIME =", elapsed_real_time, end='')
            print(" ",self.name,"published msg=",msg)

    # main behavior of the device
    def behavior(self):
        
        self.start_real_time = time.perf_counter()
        while True:
            # wait for 1 sec
            yield self.env.timeout(1)
            
            # publish a message
            self.publish(json.dumps({"sender": self.name, "sensor_value":100+self.published_count}))
        
    # end the subscription thread
    def end(self):
        self.subscribe_thread.stop()

      
