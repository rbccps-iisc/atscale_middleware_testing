#! python3
# wrapper for testbench.py
from __future__ import print_function 
import logging
from testbench import *



if __name__=='__main__':
    
    # settings:
    NUM_DEVICES = 5 # streetlights
    NUM_APPS = 1    # apps
    
    # Register all entities and set up permissions in the middleware
    do_setup(num_devices=NUM_DEVICES, num_apps=NUM_APPS, logging_level=logging.DEBUG)
    
    # Run simulation.
    # The number of devices and apps used in the simulation 
    # can be a subset of those registered.
    run_simulation(num_devices=NUM_DEVICES, num_apps=NUM_APPS, simulation_time = 50, logging_level=logging.DEBUG)
    
    # cleanup queued messages
    cleanup_queued_messages(num_devices=NUM_DEVICES, num_apps=NUM_APPS, logging_level=logging.DEBUG)
 
    # De-register all entities
    do_deregistrations(logging_level=logging.DEBUG) 

