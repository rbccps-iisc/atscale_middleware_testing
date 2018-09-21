#!/usr/bin/env python3

# Simple test where an app subscribes to data
# published by a device and also controls the 
# device by sending commands on the <device>.configure channel.
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


# routines for setting up entities and permissions in the middleware
sys.path.insert(0, '../messaging')
import setup_entities

# import the device and app models.
from device_1 import Device
from app_1 import App


# Testbench
import simpy.rt

# register entities and store the info in a file "test_config.py"
def do_setup():
    devices = ["dev"+str(i) for i in range(1)]
    apps =  ["app"+str(i) for i in range(1)]
    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read-write") for a in apps for d in devices]
                        }
    registered_entities = []
    success, registered_entities = setup_entities.setup_entities(system_description)
    assert(success)
    with open('test_config.py', 'w') as f:
        f.write("\ndevices= %s"%devices)
        f.write("\napps= %s"%apps)
        f.write("\nregistered_entities= %s"%registered_entities)
        f.write("\nsystem_description= %s"%system_description)
  

def run_test():
   
    # read the apikeys etc from a file
    from test_config import devices, apps, registered_entities, system_description

    # run the simulation
    try:
        # create a SimPy Environment:
        # real-time:
        env = simpy.rt.RealtimeEnvironment(factor=1, strict=True)
        # as-fast-as-possible (non real-time):
        # env=simpy.Environment()

        device_instances={}
        app_instances={}

        # populate the environment with devices.
        for d in devices:
            name = d
            apikey = registered_entities[d]
            device_instance = Device(env=env,name=d,apikey=apikey)
            device_instances[d]=device_instance
        
        # populate the environment with apps.
        for a in apps:
            name = a
            apikey = registered_entities[a]
            app_instance = App(env=env,name=a,apikey=apikey)
            app_instances[a]=app_instance
            # if this app controls any devices, 
            # setup the control.
            for d in devices:
                if  (  ((a,d,"read-write") in system_description["permissions"])
                    or ((a,d,"write")      in system_description["permissions"])):
                    app_instance.add_device_to_be_controlled(d)

        # run simulation for a specified amount of time
        env.run(12)

        # end all subscription threads on app instances
        for d in device_instances:
            device_instances[d].end()
        for a in app_instances:
            app_instances[a].end()

    except:
        print("There was an exception")
        raise

def do_deregistrations():
    
    # read the apikeys etc from a file
    from test_config import devices, apps, registered_entities
    
    print("---------------------")
    print("De-registering all entities")
    setup_entities.deregister_entities(registered_entities)
    print("---------------------")


if __name__=='__main__':
    do_setup()
    run_test()
    do_deregistrations()
    

