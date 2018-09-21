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
        
        # create a communication interface
        self.subscribe_thread = communication_interface.SubscribeInterface("subscribe_thread", self.name, None, apikey)
        self.subscribe_thread.verbose=False

        # some state variables
        self.subscribe_count= 0
        self.start_real_time = 0
        self.data = [] # collected data

        # start a simpy process for the main device behavior
        self.process=self.env.process(self.behavior())
    
    
    # main behavior of the app
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



