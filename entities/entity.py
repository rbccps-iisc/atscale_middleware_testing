# Simpy model for a basic entity.
#
# Each entitiy spawns a messaging thread.
# The messaging thread is responsible 
# for all blocking-type or polling-based communication
# with the middleware.



#!python3
from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import simpy
import time
import json

sys.path.insert(0, '../messaging')
# routines for communicating with the ideam middleware:
import ideam_messaging
# routines for setting up entities and permissions in the middleware
import setup_entities


# lock to serialize console output
lock = threading.Lock()


class MessagingInterface(object):
    
    def __init__(self,name,apikey):
        self.name = name
        self.apikey = apikey
        
        # create queues to communicate with the parent entity
        self.publish_queue = Queue()
        self.notification_queue = Queue()
        with lock:
            print("CommunicationInterface for entitiy",self.name,"created.")

    def publish_thread(self):
        while True:
            # wait until there's a msg to be published
            msg = self.publish_queue.get()
            # send the message to the middleware
            success = ideam_messaging.publish(str(self.name), "protected", str(self.apikey), msg)
            self.publish_queue.task_done()
            with lock:
                print("CommunicationInterface for entitiy",self.name,"published a msg",msg)

class Entity(object):
    """ Entity is the base class for Device and App classes.
    Each entity has a name, and inside its init function,
    it spawns the messaging interface threads to communicate
    with the middleware.
    """
    
    def __init__(self, env, name, apikey):
        
        self.env = env
        self.name = name
        
        # create a messaging interface
        self.messaging_interface = MessagingInterface(self.name,apikey)
        t = threading.Thread(target=self.messaging_interface.publish_thread)
        t.daemon = True  
        t.start()

        # some state variables
        self.published_count =0
        self.start_real_time = 0

        # start a simpy process for the main device behavior
        self.process=self.env.process(self.behavior())
    
    
    # helper routine to publish a message
    def publish(self,msg):
        self.messaging_interface.publish_queue.put(msg)
        self.published_count +=1
        elapsed_real_time = round(time.perf_counter() - self.start_real_time,2)
        with lock:
            print("SIM TIME =",self.env.now, "REAL TIME =", elapsed_real_time, end='')
            print(" ",self.name,"published msg=",msg)

    def behavior(self):
        
        self.start_real_time = time.perf_counter()
        while (self.published_count < 10):
            # wait for 1 sec
            yield self.env.timeout(1)
            
            # publish a message
            msg = {"sender": self.name, "sensor_value":100+self.published_count}
            msg_json_str = json.dumps(msg)
            self.publish(msg_json_str)



# Testbench
import simpy.rt

if __name__=='__main__':
    
    devices = ["device"+str(i) for i in range(2)]
    apps =  ["app"]

    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read") for a in apps for d in devices]
                        }
    
    registered_entities = []
    print("---------------------")
    print("SETUP START: setting up entities and permissions from system description:")
    print(system_description)
    success, registered_entities = setup_entities.setup_entities(system_description)
    
    if success:
        print("SETUP DONE: registered entities:",registered_entities)
        print("---------------------")
        
        
        # create a SimPy Environment:
        # real-time:
        env = simpy.rt.RealtimeEnvironment(factor=1, strict=True)
        # as-fast-as-possible (non real-time):
        # env=simpy.Environment()

        entities=[]

        # populate the environment with devices.
        for i in registered_entities:
            name = i
            apikey = registered_entities[i]
            entity_instance = Entity(env=env,name=i,apikey=apikey)
            entities.append( (name,apikey,entity_instance))

        try:
            # run simulation till there are no more events.
            env.run()
        finally:
            print("---------------------")
            print("De-registering all entities")
            setup_entities.deregister_entities(registered_entities)
            print("---------------------")

