#!python3

# SimPy model for an injector.
# This module injects sensor data/state values/faults into 
# the device model at a predetermined times. 
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
import numpy as np
import visualization
from random import randint

class StateInjector(object):
    """ 
    Inject state information, sensor data and faults
    into devices.
    """
    
    def __init__(self, env):
        
        self.env = env
        
        # a dictionary of streetlight device instaces
        # <device_name>: <device_pointer>
        self.device_instances = None
        
        # create a plot for visualization
        self.plot = None
        
        # time period of the state injector
        self.period=1
        self.count=0 # variable to keep count of periods elapsed.
        
        # start a simpy process for the main behavior
        self.behavior_process=self.env.process(self.behavior())
     
        # ambient light values to cycle-through:
        self.ambient_light_values = list(np.linspace(0,1,20)) + list(np.linspace(1,0,20))
        
        
    # main behavior:
    def behavior(self):
        
        N = len(self.device_instances)
        assert(N>0)
        intensities=[0 for i in range(N)]
        activities=[0 for i in range(N)]
        faults=[0 for i in range(N)]
        ambient_light = self.ambient_light_values[0]
        activities[0]=True
        
        # Initialize the plot
        plot = visualization.PlotStreetlights("Ground Truth", N)
        while(True):
            
            # inject sensor values for ambient light
            i = self.count%(len(self.ambient_light_values))
            ambient_light = self.ambient_light_values[i]
            for d in self.device_instances:
                self.device_instances[d].ambient_light_intensity=ambient_light
             
            # inject activity
            # generate a 0 or a 1 randomly
            #new_vehicle_arrived = np.random.choice(a=[0,1],p=[0.8,0.2],replace=False)
            new_vehicle_arrived = activities[-1]
            # rotate right the activity list
            activities = [new_vehicle_arrived] + activities[:-1]
            for i,d in zip(range(N),self.device_instances):
                if activities[i]==1:
                    self.device_instances[d].behavior_process.interrupt("activity_detected")
                
            # at counts=40 
            # inject a fault into a randomly chosen device
            if(self.count == 40 or self.count==100):
                dev = randint(0,N-1)
                list(self.device_instances.values())[dev].behavior_process.interrupt("power_outage_fault")
                faults[dev]=1
            
            # wait for period
            yield self.env.timeout(self.period)
            
            # update visualization
            intensities = [ self.device_instances[d].led_light_intensity for d in self.device_instances]
            plot.update_plot(intensities, activities, faults, ambient_light)
            
            # update count    
            self.count += 1

