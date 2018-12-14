#!/usr/bin/env python3
#
# Script to do registrations and set up permissions
# in the middleware for a given system description.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys
import json

# logging
import logging
logger = logging.getLogger(__name__)

# routines for communication with the middleware
# and for registrations/deregistration etc:
sys.path.insert(0, '../messaging')
import setup_entities

if __name__=='__main__':

	# logging settings:
	logging.basicConfig(level=logging.DEBUG)

	# suppress debug messages from other modules used.
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("pika").setLevel(logging.WARNING)
	logging.getLogger("corinthian_messaging").setLevel(logging.WARNING)
	logging.getLogger("setup_entities").setLevel(logging.INFO)

	
	# system description:
	NUM_DEVICES = 1 
	NUM_APPS    = 1
	devices = ["streetlight"+str(i) for i in range(NUM_DEVICES)]
	apps = ["controlapp"+str(i) for i in range (NUM_APPS)]
	system_description = {  "devices"       : devices,
	                        "apps"          : apps,
	                        "permissions"   : [ (a,d,"read-write") for a in apps for d in devices ]
	                    }
	registration_info_modulename = "registration_info"
	registration_info_filename = registration_info_modulename+".py"
	
	# REGISTRATIONS
	with open(registration_info_filename, "w+") as f:
		success, registered_entities = setup_entities.register_entities(system_description,f)
	assert(success)
	
