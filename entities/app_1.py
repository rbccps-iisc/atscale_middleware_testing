#!/usr/bin/env python3

# Simpy model for a basic app
# that periodically subscribes to device data 
# from the middleware and prints all collected data.
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

class App(object):
    """ An app simply polls the middleware for data at regular
    intervals and prints it.
    Each app has a name, and inside its init function,
    it spawns threads to communicate with the middleware.
    """
    
    def __init__(self, env, name, apikey):
        
        self.env = env
        self.name = name
        self.apikey = apikey
        
        # create a communication interface
        self.subscribe_thread = communication_interface.SubscribeInterface("subscribe_thread", self.name, self.name, None, apikey)
        self.subscribe_thread.verbose=False


        # some state variables
        self.subscribe_count= 0
        self.start_real_time = 0
        self.data = [] # data collected from subscribe requests

        # dictionary of devices being controlled by this app.
        self.controlled_devices={}

        # start a simpy process for the main device behavior
        self.process=self.env.process(self.behavior())
    
    def add_device_to_be_controlled(self,device_name):
        # add a device to the list of devices
        # controlled by this app over the middleware.
        
        # create a communication interface for this device:
        publish_thread = communication_interface.PublishInterface("control_thread_"+device_name, self.name, device_name, "configure", self.apikey)
        publish_thread.verbose=True
        self.controlled_devices[device_name] = publish_thread

    def send_control_message(self,device_name, msg):
        # routine to send a control message
        # to a device.
        assert(device_name in self.controlled_devices)
        publish_thread = self.controlled_devices[device_name]
        publish_thread.queue.put(msg)
        elapsed_real_time = round(time.perf_counter() - self.start_real_time,2)
        with print_lock:
            print("SIM TIME =",self.env.now, "REAL TIME =", elapsed_real_time, end='')
            print(" ",self.name,"sent a control message to device",device_name,"msg=",msg)
  

    # main behavior of the app:
    # subscribe to data from devices, and 
    # send control messages to them
    def behavior(self):
        
        self.start_real_time = time.perf_counter()
        while True:
            
            # try to pull all accummulated messages from the queue
            while not self.subscribe_thread.queue.empty():
                msg = self.subscribe_thread.queue.get()
                self.subscribe_count +=1
                self.data.append(msg)
            
            # print status msg
            elapsed_real_time = round(time.perf_counter() - self.start_real_time,2)
            with print_lock:
                print("SIM TIME =",self.env.now, "REAL TIME =", elapsed_real_time, end='')
                print(" ",self.name,"collected ",self.subscribe_count,"messages so far.")
            
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
        with print_lock:
            print(self.name,"collected the following data:")
            print("------------")
            for i in self.data:
                print(i)
            print("------------")



