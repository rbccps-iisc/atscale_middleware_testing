#!python3

# SimPy model for a smart streetlight.
#
# Behavior:
#    Periodically publish sensor data to the middleware.
#    Periodically check for, and respond to commands from the middleware.
#    Adjust the LED light intensity according to the ambient light level:
#        When ambient light level >= 0.8 (day-time), turn OFF the light.
#        When ambient light level < 0.8, turn ON the light
#        and set brightness level to 0.2 (dim)
#    Whenever the LED light is ON and the activity sensor detects an object
#        Set brightness level to 1.
#        Inform the neighbouring N streetlights about the activity detected.
#        Publish information about the activity detected to the middleware.
#    When informed by a neighbouring streetlight about activity detected, 
#    set the brightness level to 1. 
#    Whenever the light is ON, but no activity is
#    detected for a certain amount of time, dim the light again
#    (set brightness to 0.2).
#
#  Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import threading
from queue import Queue
import simpy
import json
import logging
logger = logging.getLogger(__name__)
from math import inf 
from string import digits

# helper class for communication with the middleware
sys.path.insert(0, '../messaging')
import communication_interface
DEV_PROTOCOL = "AMQP" # can be either "AMQP" or "HTTP"


class Streetlight(object):
    
    def __init__(self, env, name, apikey):
        
        self.env = env
        self.name = name # unique identifier for the device
        # id: unique integer (0 ..N) that identifies each streetlight 
        self.id = ''.join(c for c in name if c in digits) 
        self.period = 1  # time interval (in seconds) for publishing sensor data
        
        # settings (constants) for the streetlight behavior
        self.DIM_INTENSITY = 0.2            # intensity when light is dimmed
        self.AMBIENT_LIGHT_THRESHOLD = 0.8  # threshold for turning on/off the led
        self.AUTOMATIC_DIM_TIMEOUT = 2      # dim the light automatically after these many periods of inactivity
     
        # max number of messages to be published.
        # set to inf to publish unlimited messages
        self.max_published_messages = inf
        
        # variables to hold sensor values 
        # and state of the streetlight
        self.ambient_light_intensity = 1
        self.led_light_intensity =0
        self.activity_detected=0
        self.led_light_ON=False
        
        # pointers to neighbouring streetlights 
        # for direct communication (stored as a python list)
        self.neighbouring_streetlights=None
        
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
     
        # start a simpy process which models a countdown timer
        # for dimming the light automatically
        self.automatically_dim_count = self.AUTOMATIC_DIM_TIMEOUT # initialize the timer
        self.dim_process=self.env.process(self.automatically_dim())
        
        
    # main behavior of the device :
    def behavior(self):
        
        while (True): # the main loop.
            try:
                if self.state == "NORMAL":
                    
                    
                    # if the LED light was OFF but ambient light is low,
                    # turn ON the LED light
                    if(self.led_light_ON == False and self.ambient_light_intensity<self.AMBIENT_LIGHT_THRESHOLD):
                        self.led_light_ON = True
                        self.led_light_intensity = self.DIM_INTENSITY # set brightness to dim
                        logger.debug("SIM_TIME:{} ENTITY:{} turning ON LED light."
                            " Ambient light intensity = {}".format(self.env.now, self.name, self.ambient_light_intensity))
                        
                    # if the light was ON, but its daytime, turn the light OFF
                    if(self.led_light_ON==True and self.ambient_light_intensity >=self.AMBIENT_LIGHT_THRESHOLD):
                        self.led_light_ON = False # turn OFF the light
                        self.led_light_intensity=0                    
                        logger.debug("SIM_TIME:{} ENTITY:{} turning OFF LED light."
                            " Ambient light ={}".format(self.env.now, self.name, self.ambient_light_intensity))
                 
                    # periodically publish sensor data to the middleware.
                    # Publish at most <max_published_messages> messages.
                    if(self.published_count < self.max_published_messages):
                        self.publish_sensor_data()
                    
                    # periodically check for commands from the middleware if any
                    msgs = self.get_unread_messages()
                    if msgs!=None:
                        self.received_messages.extend(msgs)
                        logger.debug("SIM_TIME:{} ENTITY:{} picked up {} message(s) and has collected {}"
                            "messages in total so far.".format(self.env.now, self.name, len(msgs), self.subscribed_count))
                    
                    
                    # wait till the next clock cycle
                    yield self.env.timeout(self.period)
                    
                    # reset the activity sensor
                    self.activity_detected=0
                 
                 
                 
                elif self.state == "FAULT":
                    
                    # stay in the fault state permanently
                    # and just be un-responsive.
                    yield self.env.timeout(self.period)
                    
                else:
                    assert(0),"Invalid device state"
                    
            
            except simpy.Interrupt as i:
                # a simpy interrupt occured.
                logger.debug("SIM_TIME:{} ENTITY:{} was interrupted because of {}".format(self.env.now, self.name,i.cause))
                
                # respond according to the type of the interrupt:
                if(i.cause=="activity_detected" or i.cause=="activity_detected_in_neighbourhood"):
                    # check if the light should respond to this activity.
                    # Don't do anything if its already daytime or the light is OFF.
                    if(self.led_light_ON and self.state=="NORMAL"):
                        # set brightness level to max
                        self.led_light_intensity=1
                        # set a timer, after which the light will be dimmed again
                        # if no activity is detected for a while.
                        self.reset_automatically_dim_timer()
                        
                        if(i.cause=="activity_detected"):
                            self.activity_detected=1
                            # inform neighbouring N streetlights
                            for sl in self.neighbouring_streetlights:
                                sl.behavior_process.interrupt("activity_detected_in_neighbourhood")
                            # publish a message to inform the middleware
                            self.publish_sensor_data()
                 
                elif(i.cause=="power_outage_fault"):
                    # go into fault state.
                    self.led_light_ON=False
                    self.led_light_intensity=0
                    self.state="FAULT"
                    logger.info("SIM_TIME:{} ENTITY:{} entered the FAULT state.".format(self.env.now, self.name))
                

    # automatically dim the light if no activity 
    # is detected for a certain amount of time
    def reset_automatically_dim_timer(self):
        # reset timer
        self.automatically_dim_count = self.AUTOMATIC_DIM_TIMEOUT

    
    # countdown timer for automatically dimming the light
    # if no activity is detected for a while
    def automatically_dim(self):
        
        while (True):
            yield self.env.timeout(self.period)
            if (self.automatically_dim_count > 0):
                self.automatically_dim_count -= 1
                if (self.automatically_dim_count ==0):
                    # dim the light
                    if(self.led_light_ON and self.led_light_intensity > self.DIM_INTENSITY):
                        self.led_light_intensity=self.DIM_INTENSITY
                        logger.debug("SIM_TIME:{} ENTITY:{} dimming the LED light".format(self.env.now, self.name))
                        # publish sensor data to the middleware
                        self.publish_sensor_data()


    # publish a message to the middleware
    def publish(self,msg):
        self.publish_thread.queue.put(msg)
        self.published_count +=1
        logger.debug("SIM_TIME:{} ENTITY:{} published message:{}".format(self.env.now,self.name, msg))
    
    # publish sensor data
    def publish_sensor_data(self):
        data = {"sender_name":self.name,
                "sender_id":self.id,
                "ambient_light_intensity": self.ambient_light_intensity,
                "led_light_intensity": self.led_light_intensity,
                "activity_detected": self.activity_detected,
                "operational_status":"OK",
                "fault_info":"none"
                }
        self.publish(json.dumps(data))
    
    # publish fault information
    def publish_fault_information(self):
        data = {"sender_name":self.name,
                "sender_id":self.id,
                "ambient_light_intensity":0,
                "led_light_intensity":0,
                "activity_detected":0,
                "operational_status":"FAULT",
                "fault_info":"sensor_failure"
                }
        self.publish(json.dumps(data))
 
 
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

