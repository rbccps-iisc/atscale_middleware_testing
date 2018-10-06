#!python3

# SimPy model for a basic device.
# The device simply publishes data to the 
# middleware and checks for any commands
# from the middleware at regular intervals.
#
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import simpy
import json
import logging
logger = logging.getLogger(__name__)


# helper class for communication with the middleware
sys.path.insert(0, '../messaging')
import communication_interface

DEV_PROTOCOL = "AMQP" # can be either "AMQP" or "HTTP"

class Device(object):
    """ 
    A device simply publishes data to the middleware 
    at regular intervals. Each device has a name, and 
    inside its init function, it spawns some threads 
    to communicate with the middleware.  
    """
    
    def __init__(self, env, name, apikey):
        
        self.env = env
        self.name = name # unique identifier for the device
        self.period = 1  # operational clock period for the device (in seconds)
        
        # set up communication interfaces
        #   publish interface:
        self.publish_thread = communication_interface.PublishInterface(
            interface_name="publish_thread", entity_name=name, 
            apikey=apikey, exchange=str(name)+".protected", protocol=DEV_PROTOCOL)
        
        #   subscribe interface
        self.subscribe_thread = communication_interface.SubscribeInterface(
            interface_name="subscribe_thread", entity_name=name, 
            apikey=apikey, exchange=str(name)+".configure", protocol=DEV_PROTOCOL)
            
        # some state variables
        self.state = "NORMAL"       # state of the device. ("NORMAL"/"FAULT")
        self.published_count = 0    # number of messages sent
        self.subscribed_count= 0    # number of messages received
        self.received_messages =[]  # list of messages received by the device
        
        # start a simpy process for the main device behavior
        self.behavior_process=self.env.process(self.behavior())
        
        
        
    # main behavior of the device :
    def behavior(self):
        
        
        while (self.published_count<10): # the main loop.
            try:
                if self.state == "NORMAL":
                    # periodically publish sensor data
                    # and check for messages from the middleware.
                    self.publish(json.dumps({"sender": self.name, 
                        "sensor_value":100+self.published_count}))
                    msgs = self.get_unread_messages()
                    if msgs!=None:
                        self.received_messages.extend(msgs)
                        logger.debug("SIM_TIME:{} ENTITY:{} picked up {} message(s) and has collected {} messages in total so far.".format(self.env.now, self.name, len(msgs), self.subscribed_count))
                        
                    # wait till the next clock cycle
                    yield self.env.timeout(self.period)
                 
                 
                 
                elif self.state == "FAULT":
                    logger.info("SIM_TIME:{} ENTITY:{} entered the FAULT state.".format(self.env.now, self.name))
                    # send a "fault" status to the app
                    self.publish(json.dumps({"sender": self.name, "status":"FAULT"}))
                    
                    # keep waiting for a "resume" response from the app
                    self.resume_command_received = False
                    while(not self.resume_command_received):
                        msgs = self.get_unread_messages()
                        if msgs!=None:
                            self.received_messages.extend(msgs)
                            for m in msgs:
                                if "command" in m:
                                    if (m["command"]=="RESUME"):
                                        self.resume_command_received=True
                                        logger.info("SIM_TIME:{} ENTITY:{} received a RESUME command".format(self.env.now, self.name))
                                     
                                     
                        # wait till the next clock cycle
                        yield self.env.timeout(self.period)
                    # resume command received.
                    # go back to normal state.
                    self.state="NORMAL"
                    
                else:
                    assert(0),"Invalid device state"
                    
            
            except simpy.Interrupt as i:
                # a simpy interrupt occured.
                # check that this was a fault injected.
                logger.info("SIM_TIME:{} ENTITY:{} was interrupted because of {}".format(self.env.now, self.name,i.cause))
                # go into fault state.
                self.state="FAULT"
                



    # publish a message to the middleware
    def publish(self,msg):
        self.publish_thread.queue.put(msg)
        self.published_count +=1
        logger.debug("SIM_TIME:{} ENTITY:{} published message:{}".format(self.env.now,self.name, msg))
    
    # check if there are messages/commands received
    # in the subscribe queue.
    def get_unread_messages(self):
        unread_messages=[]
        if self.subscribe_thread.queue.empty():
            return None
        else:
            while not self.subscribe_thread.queue.empty():
                msg = self.subscribe_thread.queue.get()
                self.subscribed_count +=1
                unread_messages.append(msg)
            return unread_messages 
       
    # IMPORTANT!:
    # stop all communication threads.
    def end(self):
        self.subscribe_thread.stop()
        self.publish_thread.stop()
        logger.info("SIM_TIME:{} ENTITY:{} stopping. Collected {} messages in total.".format(self.env.now, self.name, self.subscribed_count))
        for msg in self.received_messages:
            logger.debug("\t MESSAGE:{}".format(msg))




#------------------------------------
# Testbench
#------------------------------------
if __name__=='__main__':
    
    import setup_entities
    import simpy.rt


    # logging settings:
    logging.basicConfig(level=logging.DEBUG)
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("communication_interface").setLevel(logging.WARNING)

    devices = ["foo"]
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

