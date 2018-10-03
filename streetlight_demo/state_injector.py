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

class StateInjector(object):
    """ 
    Inject state information, sensor data and faults
    into devices.
    """
    
    def __init__(self, env):
        
        self.env = env
        
        # a dictionary of device instaces
        # <device_name>: <device_pointer>
        self.device_instances = None
        
        # create a plotter for visualization
        self.plot = None
        
        # start a simpy process for the main behavior
        self.period=1
        self.behavior_process=self.env.process(self.behavior())

        # model ambient light variation
        self.num_values = 20 # total number of values to cycle through
        self.ambient_light_values = list(np.linspace(0,1,self.num_values)) + list(np.linspace(1,0,self.num_values))
        
        self.count=0 # starting value


        
    # main behavior:
    def behavior(self):
        
        N = len(self.device_instances)
        assert(N>0)

        intensities=[0 for i in range(N)]
        activities=[0 for i in range(N)]
        ambient_light = self.ambient_light_values[0]
        
        # Initialize the plotter
        plot = visualization.PlotStreetlights(N, intensities, activities, ambient_light)
        
        while(True):
            
            # inject sensor values for ambient light
            i = self.count%(len(self.ambient_light_values))
            ambient_light = self.ambient_light_values[i]
            for d in self.device_instances:
                self.device_instances[d].ambient_light_intensity=ambient_light

            # inject activity
            activities = [np.random.choice(a=[0,1],p=[0.8,0.2],replace=False)] + activities[:-1]
            for i,d in zip(range(N),self.device_instances):
                if activities[i]==True:
                    self.device_instances[d].behavior_process.interrupt("activity_detected")
            
            
            # wait for period
            yield self.env.timeout(self.period)
            
            # update visualization
            intensities = [ self.device_instances[d].led_light_intensity for d in self.device_instances]
            plot.update_plot(intensities, activities, ambient_light)
            
            # update count    
            self.count += 1

