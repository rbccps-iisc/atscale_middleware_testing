#!python3 
#
# Interfaces for performing non-blocking 
# communication with the middleware.
# There are two types of interfaces: 
#   PublishInterface : sends messages to the middleware
#   SubscribeInterface : obtains messages from the middleware via polling
#
# Each entity (device or app) can spawn multiple such interfaces.
# Each interface becomes an independent thread and 
# communicates with the parent entity using queues.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import json

# routines for communicating with the ideam middleware
# and setting up registrations and permissions.
import ideam_messaging

# lock to serialize console output
print_lock = threading.Lock()


class CommunicationInterface(object):
    """ Base class for publish/subscribe interfaces."""
    
    def __init__(self, interface_name, parent_entity_name, target_entity_name, stream, apikey):
        
        # name of this messaging interface.
        # because one entity can own multiple interfaces
        self.interface_name = interface_name 

        # name of the parent entity that owns this interface
        self.parent_entity_name = parent_entity_name
        
        # create queues to communicate with the parent entity
        self.queue = Queue()
        
        # communication settings
        self.target_entity_name = target_entity_name # name of the entity to be used as exchange name for publish/subscribe.
        self.stream=stream # stream (protected/public/configuration/notify etc)
        self.apikey = apikey # apikey
        
        # verbosity settings.
        # print stuff to console when verbose is True.
        self.verbose = True

        # some useful variables
        self.name = self.parent_entity_name + "." + self.interface_name
        self.message_count =0

class PublishInterface(CommunicationInterface):
    
    def __init__(self, interface_name, parent_entity_name, target_entity_name, stream, apikey):
        CommunicationInterface.__init__(self, interface_name, parent_entity_name, target_entity_name, stream, apikey)
        
        # spawn the behaviour function as an independent thread
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.behavior)
        self.thread.daemon = True
        self.thread.start()
        
        if self.verbose:
            with print_lock:
                print("Thread",self.name,"created.")
    
    # function to stop the thread from outside
    def stop(self):
        self.stop_event.set()
        if self.verbose:
            with print_lock:
                print("Thread",self.name,"stopped.")

    # check if the thread was stopped.
    def stopped(self):
        return self.stop_event.is_set()
    
    def behavior(self):
        while not self.stopped():
            # wait until there's a msg to be published
            msg = self.queue.get()
            # send the message to the middleware
            success = ideam_messaging.publish(self.target_entity_name, self.stream, self.apikey, msg)
            assert(success)
            if self.verbose:
                with print_lock:
                    print("Thread",self.name,"published message",msg)
            self.message_count +=1
            self.queue.task_done()


class SubscribeInterface(CommunicationInterface):
    
    def __init__(self, interface_name, parent_entity_name, target_entity_name, stream, apikey):
        CommunicationInterface.__init__(self, interface_name, parent_entity_name, target_entity_name, stream, apikey)
        
      
      # spwan the behaviour function as an independent thread
        self.polling_interval = 1 # time (in seconds) between subscribe requests
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.behavior)
        self.thread.daemon = True
        self.thread.start()
        if self.verbose:
            with print_lock:
                print("Thread",self.name,"created.")
    
    # function to stop the thread from outside
    def stop(self):
        self.stop_event.set()
        if self.verbose:
            with print_lock:
                print("Thread",self.name,"stopped.")

    # check if the thread was stopped.
    def stopped(self):
        return self.stop_event.is_set()
    
    def behavior(self):

        while not self.stop_event.wait(timeout=self.polling_interval):
            # subscribe from middleware
            success, response = ideam_messaging.subscribe(self_id=self.target_entity_name,stream=self.stream, 
                apikey=self.apikey, max_entries=100)
            assert(success)
            r = response.json()
            for entry in r:
                # push the message into the queue
                self.queue.put(entry)
                self.message_count += 1
                if self.verbose:
                    with print_lock:
                        print("Thread",self.name,"received msg = ",entry)



# Testbench
import setup_entities
import time

if __name__=='__main__':
    
    devices = ["dev"]
    apps =  ["app"]

    system_description = {  "entities" : devices+apps,
                            "permissions" : [(a,d,"read") for a in apps for d in devices]
                        }
    registered_entities = []
     
    try:
        # register a device and an app and set up permissions
        success, registered_entities = setup_entities.setup_entities(system_description)
        assert(success)
        
        # create two publish threads for "dev"
        p1 = PublishInterface("p1","dev","dev","protected",registered_entities["dev"])
        p2 = PublishInterface("p2","dev","dev","protected",registered_entities["dev"])
        
        # create one subscribe thread for "app"
        s1 = SubscribeInterface("s1","app","app", None, registered_entities["app"])

        # push something into the publish queue
        NUM_MSG = 10
        for i in range (NUM_MSG):
            p1.queue.put( json.dumps({"sender": "p1", "value":str(i)}))
            p2.queue.put( json.dumps({"sender": "p2", "value":str(i)}))

        time.sleep(2)

        # pull messages from the subscribe queue
        count=0
        print("The following messages were present in the subscribe queue:")
        while(count<NUM_MSG*2):
            msg = s1.queue.get()
            print(msg)
            count+=1


        #stop all child threads
        p1.stop()
        p2.stop()
        s1.stop()
        
    finally:
        print("---------------------")
        print("De-registering all entities")
        setup_entities.deregister_entities(registered_entities)
        print("---------------------")

