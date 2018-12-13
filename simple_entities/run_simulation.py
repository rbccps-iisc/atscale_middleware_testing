#!/usr/bin/env python3

# Script for running a SimPy simulation with simple_device and simple_app models.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import simpy
import time
import json
import simpy.rt

# logging
import logging
logger = logging.getLogger(__name__)

# import the entity models.
from simple_device import SimpleDevice
from simple_app import SimpleApp
#from simple_injector import SimpleInjector

# a dummy SimPy process to print simulation time and real time
def print_time(env):
    start_real_time = time.perf_counter()
    max_overshoot = 0.0
    PERIOD = 1
    while True:
        elapsed_real_time = round(time.perf_counter() - start_real_time,2)
        sim_time = float(env.now)
        logger.info("SIM_TIME:{} REAL_TIME:{}------------".format(sim_time, elapsed_real_time))
        # check if the real-time overshot simulation time 
        # by more than <PERIOD> seconds.
        if ( (elapsed_real_time - sim_time) >= float(PERIOD)):
            overshoot = elapsed_real_time - sim_time
            max_overshoot = max(overshoot, max_overshoot)
            logger.warning("Simulation time overshot real-time by {:.3f}s. Max_overshoot so far was {:.3f}s.".format(overshoot,max_overshoot))
        yield env.timeout(PERIOD)


def run_simulation(registration_info_modulename, num_devices, num_apps, simulation_time, logging_level=logging.INFO):
	"""
	Run simulation for <simulation_time> seconds.
	The logging_level can be logging.DEBUG or logging.INFO etc.
	
	This function assumes that all the devices and apps 
	have been pre-registered with the middleware 
	and the registration information has been written into 
	the .py file "registration_info_modulename".
	
	The number of entities <num_devices> and <num_apps>
	to be used for the simulation needs to be specified
	as this can be a subset of the total entities registered.
	"""
	
	# logging settings:
	logging.basicConfig(level=logging_level) 
	
	# read the apikeys for pre-registered devices from file  
	import importlib
	c = importlib.import_module(registration_info_modulename, package=None)
	registered_entities = c.registered_entities
	
	# the list of devices and apps used for the simulation
	# can be a subset of those registered.
	assert(num_devices>0 and num_devices<=len(c.devices))
	assert(num_apps>0 and num_apps<=len(c.apps))
	assert(simulation_time>0)
	
	devices = c.devices[0:num_devices]
	apps = c.apps[0:num_apps]
	
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
		    apikey = registered_entities[d]
		    device_instance = SimpleDevice(env=env,ID=d,apikey=apikey)
		    device_instances[d]=device_instance
		
		# populate the environment with apps.
		for a in apps:
		    apikey = registered_entities[a]
		    app_instance = SimpleApp(env=env,ID=a,apikey=apikey)
		    app_instances[a]=app_instance
		
		# for each app, provide a list of devices that it should control.
		# it is assumed that each app controls each of the devices.
		for a in apps:
			app_instances[a].controlled_devices = devices
		
		# Create a fault injector 
		# that injects faults into devices
		# fault_inj = FaultInjector(env=env)
		# fault_inj.device_instances = device_instances
		
		# create a dummy simpy process that simply prints the
		# simulation time and real time.
		time_printer = env.process(print_time(env))
		
		# run simulation for a specified amount of time
		assert(simulation_time > 0)
		assert(isinstance(simulation_time, int))
		print("Running simulation for",simulation_time,"seconds ....")
		env.run(simulation_time)
		
		# insert a delay here for all simulation
		# to end before closing the threads.
		print("Simulation ended. Closing all threads...")
		time.sleep(1)
		# end all subscription threads on all entities
		for d in device_instances:
		    device_instances[d].end()
		for a in app_instances:
		    app_instances[a].end()
		time.sleep(1)
		
	except:
		print("There was an exception")
		raise




if __name__=='__main__':

	# logging settings:
	logging.basicConfig(level=logging.DEBUG)

	# suppress debug messages from other modules used.
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("pika").setLevel(logging.WARNING)
	logging.getLogger("corinthian_messaging").setLevel(logging.WARNING)
	logging.getLogger("communication_interface").setLevel(logging.INFO)
	logging.getLogger("simple_device").setLevel(logging.DEBUG)
	logging.getLogger("simple_app").setLevel(logging.DEBUG)

	
	# system description:
	registration_info_modulename = "registration_info"
	registration_info_filename = registration_info_modulename+".py"
	
	
	# RUN SIMULATION
	num_devices_to_simulate = 1
	num_apps_to_simulate = 1
	sim_time = 10
	run_simulation(registration_info_modulename, num_devices_to_simulate, num_apps_to_simulate, sim_time)
		
	
