#! python3

# Simple test where an app subscribes to data
# published by a device and also controls the 
# device by sending commands on the <device>.configure channel.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import simpy
import time
import json
import simpy.rt
import logging
logger = logging.getLogger(__name__)


# routines for setting up entities and permissions in the middleware
sys.path.insert(0, '../messaging')
import setup_entities

# import the device and app models.
from simple_device import Device
from simple_app import App



# register entities and store the info in a file "simple_test_config.py"
def do_setup():
    
    print("Setting up registrations and permissions...",end='')
    devices = ["dev"+str(i) for i in range(2)]
    apps =  ["app"+str(i) for i in range(2)]
    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read-write") for a in apps for d in devices]
                        }
    registered_entities = []
    success, registered_entities = setup_entities.setup_entities(system_description)
    assert(success)
    with open('simple_test_config.py', 'w') as f:
        f.write("\ndevices= %s"%devices)
        f.write("\napps= %s"%apps)
        f.write("\nregistered_entities= %s"%registered_entities)
        f.write("\nsystem_description= %s"%system_description)
    print("...done.")
  

def run_test():
    # read the apikeys etc from file "simple_test_config.py"
    from simple_test_config import devices, apps, registered_entities, system_description

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
        
        # setup control permissions between apps and devices
        for p in system_description["permissions"]:
            a = p[0]    # app name
            d = p[1]    # device name
            perm = p[2] # permission

            if(perm=="write" or perm=="read-write"):
                app_instances[a].add_device_to_be_controlled(d)

        # run simulation for a specified amount of time
        simulation_time=12
        print("Running simulation for",simulation_time,"seconds ....")
        env.run(12)

        # end all subscription threads on all entities
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
    
    # logging settings:
    logging.basicConfig(level=logging.DEBUG)
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    #logging.getLogger("communication_interface").setLevel(logging.WARNING)

    do_setup()
    run_test()
    #do_deregistrations()
    

