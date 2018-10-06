#!python3 
#
# Interfaces for performing non-blocking communication with the middleware.
# Entities registered with the middleware can own multiple such interfaces.
# Each interface becomes an independent thread and communicates with the parent entity using queues.
#
# There are two types of interfaces: 
#   PublishInterface : sends messages to the middleware
#   SubscribeInterface : obtains messages from the middleware via polling
# 
# An interface can use either HTTP or AMQP protocols for communication.
# This can configured by letting protocol="HTTP" or protocol="AMQP"
# at the time creating the interface.
# 
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import json
import logging
logger = logging.getLogger(__name__)

# routines for communicating with the ideam middleware
# and setting up registrations and permissions.
import ideam_messaging


class CommunicationInterface(object):
    """ Base class for publish/subscribe interfaces."""
    
    def __init__(self, interface_name, entity_name, apikey, exchange):
        
        # name of this messaging interface.
        # because one entity can own multiple interfaces
        self.interface_name = interface_name 

        # name and apikey of the entity that owns this interface
        self.entity_name = entity_name
        self.apikey = apikey
        
        # exchange/queue to publish/subscribe
        self.exchange = exchange
        
        # create queues to communicate with the parent entity
        self.queue = Queue()
        
        # some useful variables
        self.name = self.entity_name + "." + self.interface_name
        self.message_count =0


class PublishInterface(CommunicationInterface):
    
    def __init__(self, interface_name, entity_name, apikey, exchange, protocol):
        CommunicationInterface.__init__(self, interface_name, entity_name, apikey, exchange)
        
        # check if the protocol to be used is HTTP or AMQP
        assert(protocol=="HTTP" or protocol == "AMQP")
        self.protocol = protocol # protocol to be used for the communication.
        if(protocol=="AMQP"):
            self.amqp_channel = ideam_messaging.PublishChannel(entity_name, apikey, exchange)
        
        # spawn the behaviour function as an independent thread
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.behavior)
        self.thread.daemon = True
        self.thread.start()
        logger.info("thread {} created.".format(self.name))
    
    # function to stop the thread from outside
    def stop(self):
        self.stop_event.set()
        if(self.protocol=="AMQP"):
            self.amqp_channel.close()
        logger.info("thread {} stopped.".format(self.name))

    # check if the thread was stopped.
    def stopped(self):
        return self.stop_event.is_set()
    
    def behavior(self):
        while not self.stopped():
            # wait until there's a msg to be published
            msg = self.queue.get()
            # send the message to the middleware
            if(self.protocol=="HTTP"):
                success = ideam_messaging.publish(apikey=self.apikey, exchange=self.exchange, data=msg)
            else:
                success = self.amqp_channel.publish(exchange=self.exchange, data=msg)
            assert(success)
            logger.debug("thread {} published a message: {}".format(self.name, msg))
            self.message_count +=1


class SubscribeInterface(CommunicationInterface):
    
    def __init__(self, interface_name, entity_name, apikey, exchange, protocol):
        CommunicationInterface.__init__(self, interface_name, entity_name, apikey, exchange)
         
        # check if the protocol to be used is HTTP or AMQP
        assert(protocol=="HTTP" or protocol == "AMQP")
        self.protocol = protocol # protocol to be used for the communication.
        if(protocol=="AMQP"):
            self.amqp_channel = ideam_messaging.SubscribeChannel(entity_name, apikey, exchange)
      
      # spwan the behaviour function as an independent thread
        self.polling_interval = 1 # time (in seconds) between subscribe requests
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.behavior)
        self.thread.daemon = True
        self.thread.start()
        logger.info("thread {} created.".format(self.name))
    
    # function to stop the thread from outside
    def stop(self):
        self.stop_event.set()
        if(self.protocol=="AMQP"):
            self.amqp_channel.close()
        logger.info("thread {} stopped.".format(self.name))

    # check if the thread was stopped.
    def stopped(self):
        return self.stop_event.is_set()
    
    def behavior(self):

        while not self.stop_event.wait(timeout=self.polling_interval):
            # subscribe from middleware
            if(self.protocol=="HTTP"):
                success, messages = ideam_messaging.get(apikey=self.apikey, queue=self.exchange, max_entries=10000)
                assert(success)
                for m in messages:
                    # push the message into the queue
                    self.queue.put(m)
                    self.message_count += 1
                    logger.debug("thread {} received a message: {}".format(self.name,m))
            else:
                success, messages = self.amqp_channel.get(queue=self.exchange, max_entries=10000)
                for m in messages:
                    # push the message into the queue
                    self.queue.put(m)
                    self.message_count += 1
                    logger.debug("thread {} received a message: {}".format(self.name,m))


#------------------------------------
# Testbench
#------------------------------------
import setup_entities
import time

if __name__=='__main__':
    
    # logging settings:
    logging.basicConfig(level=logging.DEBUG)
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)

    devices = ["device1", "device2"]
    apps =  ["application1","application2"]

    system_description = {  "entities" : devices+apps,
                            "permissions" : [("application1","device1","read"), ("application2","device2","read")]
                        }
    registered_entities = []
     
    # register a device and an app and set up permissions
    success, registered_entities = setup_entities.setup_entities(system_description)
    assert(success)
    
    # create publish threads for "device1" and "device2"
    p1 = PublishInterface("p1","device1",registered_entities["device1"],"device1.protected",protocol="HTTP")
    p2 = PublishInterface("p2","device2",registered_entities["device2"],"device2.protected",protocol="AMQP")
    
    # create subscribe threads for "application1" and "application2"
    s1 = SubscribeInterface("s1","application1",registered_entities["application1"], "application1",protocol="HTTP")
    s2 = SubscribeInterface("s2","application2",registered_entities["application2"], "application2",protocol="AMQP")

    try:
        # push something into each of the publish queues
        NUM_MSG = 10
        for i in range (NUM_MSG):
            p1.queue.put( json.dumps({"sender": "p1", "value":str(i)}))
            p2.queue.put( json.dumps({"sender": "p2", "value":str(i)}))

        time.sleep(2)

        # pull messages from the subscribe queues
        count=0
        print("The following messages were present in the subscribe queue for application1:")
        while(count<NUM_MSG):
            msg = s1.queue.get()
            print(msg)
            count+=1
        
        count=0
        print("The following messages were present in the subscribe queue for application2:")
        while(count<NUM_MSG):
            msg = s2.queue.get()
            print(msg)
            count+=1
    except:
        raise
    finally:
        #stop all child threads
        p1.stop()
        p2.stop()
        s1.stop()
        s2.stop()
        print("---------------------")
        print("De-registering all entities")
        setup_entities.deregister_entities(registered_entities)
        print("---------------------")

