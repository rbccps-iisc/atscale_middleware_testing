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
from fault_injector import FaultInjector

# information (apikeys) of all registered entities are
# stored in a file for easy re-use.
CONFIG_MODULE = "simple_test_config"
CONFIG_FILE_NAME = CONFIG_MODULE+".py"


# register entities and store the info in a file
def do_setup():
    
    print("Setting up registrations and permissions...")
    
    NUM_DEVICES = 1
    NUM_APPS = 1

    devices = ["dev"+str(i) for i in range(NUM_DEVICES)]
    apps =  ["app"+str(i) for i in range(NUM_APPS)]
    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read-write") for a in apps for d in devices]
                        }
    registered_entities = []
    try:
        success, registered_entities = setup_entities.setup_entities(system_description)
        assert(success)
    
    finally:
        print("Writing info about registered entities into file",CONFIG_FILE_NAME)
        with open(CONFIG_FILE_NAME, 'w') as f:
            f.write("\nsystem_description= %s"%system_description)
            f.write("\ndevices= %s"%devices)
            f.write("\napps= %s"%apps)
            f.write("\nregistered_entities= %s"%registered_entities)
        print("...done.")
      

# a dummy SimPy process to print simulation time and real time
def print_time(env):
    start_real_time = time.perf_counter()
    while True:
        elapsed_real_time = round(time.perf_counter() - start_real_time,2)
        logger.info("SIM_TIME:{} REAL_TIME:{}".format(env.now, elapsed_real_time))
        yield env.timeout(1)

        
def run_test():
    
    # read the apikeys for pre-registered devices from file  
    import importlib
    c = importlib.import_module(CONFIG_MODULE, package=None)
    registered_entities = c.registered_entities
    # create a subset of the list of devices and apps
    # for testing:
    NUM_DEVICES = 1
    NUM_APPS = 1
    devices = ["dev"+str(i) for i in range(NUM_DEVICES)]
    apps =  ["app"+str(i) for i in range(NUM_APPS)]
    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read-write") for a in apps for d in devices]
                        }
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

        # Create a fault injector 
        # that injects faults into devices
        fault_inj = FaultInjector(env=env)
        fault_inj.device_instances = device_instances

        # create a dummy simpy process that simply prints the
        # simulation time and real time.
        time_printer = env.process(print_time(env))

        # run simulation for a specified amount of time
        simulation_time=15
        print("Running simulation for",simulation_time,"seconds ....")
        env.run(simulation_time)

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
    import importlib
    c = importlib.import_module(CONFIG_MODULE, package=None)
    registered_entities = c.registered_entities 

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
    logging.getLogger("communication_interface").setLevel(logging.WARNING)

    do_setup()
    run_test()
    do_deregistrations()
    

