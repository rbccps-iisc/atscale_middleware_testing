# Models an entity in the ideam middleware.
# This is a base class for all device/app models.

from __future__ import print_function 
import os, sys
import random
import simpy


# import the messaging library 
# for communicating with the middleware
sys.path.insert(0, '../messaging/https')
from messaging_https import *


class Entity(object):
    
    def __init__(self, env, name):
        self.env=env
        self.name=name
        self.apikey=None
        # register the device with the middleware and get the apikey
        success, self.apikey = register(self.name)
        if(success):
            print(self.name,"registration successful. Apikey = ",self.apikey)
        else:
            print(self.name,"registration failed.")

    def __del__(self):
        
        # deregister the device
        success = deregister(self.name)
        if(success):
            print(self.name,"deregistered.")
        else:
            print(self.name,"de-registration failed.")



class Device(Entity):
    
    def __init__(self, env, name, start_time):
        Entity.__init__(self,env,name)
        self.start_time = start_time
        self.process=env.process(self.behavior())
        
        # some state variables
        self.num_publish_requests=0

    def behavior(self):

        #checks:
        assert(self.apikey!=None)
        
        # wait until this device's start_time
        yield self.env.timeout(self.start_time)

        
        start = time.perf_counter()
        while (self.num_publish_requests <6):

            # wait for 1 sec
            yield self.env.timeout(2)
            end = time.perf_counter()
            print("Real time =", end - start)
            print("Sim time = ",self.env.now)

            
            # publish a message
            data = '{"temp": "'+str(100+self.num_publish_requests)+'"}'
            print(self.name,"publishing. Data=",data,".",end=''),
            success = publish(self_id=self.name, apikey=self.apikey, data=data, stream="protected")
            print("success = ",success)
            sys.stdout.flush()
            self.num_publish_requests +=1


import simpy.rt

def run_test():
    
    # Create an Environment:
    env = simpy.rt.RealtimeEnvironment(factor=2, strict=False)
    # env=simpy.Environment()

    devices=[]
    
    # Create 20 devices.
    for i in range(2):
        devices.append(Device(env,"device"+str(i),start_time=i+5))
    print("Devices = ",devices)
    env.run()


run_test()



        

