#!python3

# SimPy model for a basic device.
# The device simply publishes data
# to the middleware and checks for any commands
# from the middleware at regular intervals.
#
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


# helper class for communication with the middleware
sys.path.insert(0, '../messaging')
import communication_interface

class Device(object):
    """ 
    A device simply publishes data to the middleware 
    at regular intervals. Each device has a name, and 
    inside its init function, it spawns some threads 
    to communicate with the middleware.  
    """
    
    def __init__(self, env, name, apikey):
        
        self.env = env
        self.name = name
        self.apikey = apikey
        
        # set up communication interfaces
        #
        # publish interface:
        self.publish_thread = communication_interface.PublishInterface(
            interface_name="publish_thread", parent_entity_name=self.name, 
            target_entity_name=self.name, stream="protected", apikey=apikey)
        # subscribe interface
        self.subscribe_thread = communication_interface.SubscribeInterface(
            interface_name="subscribe_thread", parent_entity_name=self.name, 
            target_entity_name=self.name, stream="configure", apikey=apikey)

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
        logger.debug("SIM_TIME:{} REAL_TIME:{} ENTITY:{} published message:{}".format(self.env.now, 
            elapsed_real_time,self.name, msg))

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



#------------------------------------
# Testbench
#------------------------------------
if __name__=='__main__':
    
    import setup_entities
    import time
    import simpy.rt


    # logging settings:
    logging.basicConfig(level=logging.DEBUG)
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("communication_interface").setLevel(logging.WARNING)

    devices = ["dev"]
    apps =  []
    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read") for a in apps for d in devices]
                        }
    registered_entities = []
     
    try:
        # register a device and an app and set up permissions
        success, registered_entities = setup_entities.setup_entities(system_description)
        assert(success)
        
        # create a SimPy Environment:
        # real-time:
        env = simpy.rt.RealtimeEnvironment(factor=1, strict=True)
        # as-fast-as-possible (non real-time):
        # env=simpy.Environment()
        device_instances={}

        # populate the environment with devices.
        for d in devices:
            name = d
            apikey = registered_entities[d]
            device_instance = Device(env=env,name=d,apikey=apikey)
            device_instances[d]=device_instance
        
        # run simulation for a specified amount of time
        max_time=5
        print("---------------------")
        print("Running simulation for",max_time,"seconds....")
        print("---------------------")
        env.run(max_time)

        # end all communication threads owned by the entities.
        for d in device_instances:
            device_instances[d].end()

    finally:
        print("---------------------")
        print("De-registering all entities")
        setup_entities.deregister_entities(registered_entities)
        print("---------------------")

