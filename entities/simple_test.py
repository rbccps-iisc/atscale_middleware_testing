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

# logging
import logging
logger = logging.getLogger(__name__)
# suppress debug messages from other modules used.
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("communication_interface").setLevel(logging.WARNING)



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
def do_setup(num_devices, num_apps):
    
    print("Setting up registrations and permissions...")
    
    devices = ["dev"+str(i) for i in range(num_devices)]
    apps =  ["app"+str(i) for i in range(num_apps)]
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
    max_overshoot = 0.0
    PERIOD = 1
    while True:
        elapsed_real_time = round(time.perf_counter() - start_real_time,2)
        sim_time = float(env.now)
        logger.info("SIM_TIME:{} REAL_TIME:{}".format(sim_time, elapsed_real_time))
        # check if the real-time overshot simulation time 
        # by more than <PERIOD> seconds.
        if ( (elapsed_real_time - sim_time) >= float(PERIOD)):
            overshoot = elapsed_real_time - sim_time
            max_overshoot = max(overshoot, max_overshoot)
            logger.warning("Simulation time overshot real-time by {} s. Max_overshoot so far was {} s.".format(overshoot,max_overshoot))
        yield env.timeout(PERIOD)



def run_test(num_devices, num_apps):
    
    # read the apikeys for pre-registered devices from file  
    import importlib
    c = importlib.import_module(CONFIG_MODULE, package=None)
    registered_entities = c.registered_entities
    # create a subset of the list of devices and apps
    # for testing:
    devices = ["dev"+str(i) for i in range(num_devices)]
    apps =  ["app"+str(i) for i in range(num_apps)]
    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read-write") for a in apps for d in devices]
                        }
    # run the simulation
    try:
        # create a SimPy Environment:
        # real-time, but without strict checking:
        env = simpy.rt.RealtimeEnvironment(factor=1, strict=False)

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
        simulation_time=20
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
    
    # settings:
    NUM_DEVICES = 2
    NUM_APPS = 2
    
    # logging settings:
    logging.basicConfig(level=logging.INFO) # set level=logging.INFO when num. of entities is large.
    
    do_setup(NUM_DEVICES, NUM_APPS) # do entity registrations and save apikeys in file <CONFIG_FILE_NAME>
    run_test(NUM_DEVICES, NUM_APPS) # run simulation
    do_deregistrations() # de-register all entries saved in file <CONFIG_FILE_NAME>

