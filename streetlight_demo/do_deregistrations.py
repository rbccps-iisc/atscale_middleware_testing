#!/usr/bin/env python3

# Script for deregistering all entities listed in file registration_info.py
#
# Author: Neha Karanjkar

from __future__ import print_function 
import os, sys

# logging
import logging
logger = logging.getLogger(__name__)

# routines for communication with the middleware
# and for registrations/deregistratiosn etc:
sys.path.insert(0, '../messaging')
import setup_entities

def do_deregistrations(registration_info_modulename):
	""" de-register all entities specified 
	in the file (.py) registration_info_modulename.
	"""
	import importlib
	c = importlib.import_module(registration_info_modulename, package=None)
	devices = c.devices
	apps = c.apps
	logger.info("DE-REGISTER: de-registering all devices from file {}....".format(registration_info_modulename))
	setup_entities.deregister_entities(devices)
	logger.info("DE-REGISTER: de-registering all apps from file {}....".format(registration_info_modulename))
	setup_entities.deregister_entities(apps)
	logger.info("DE-REGISTER: done.")


if __name__=='__main__':

	# logging settings:
	logging.basicConfig(level=logging.DEBUG)

	# suppress debug messages from other modules used.
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("pika").setLevel(logging.WARNING)
	logging.getLogger("corinthian_messaging").setLevel(logging.WARNING)
	logging.getLogger("setup_entities").setLevel(logging.INFO)

	registration_info_modulename = "registration_info"
	registration_info_filename = registration_info_modulename+".py"
	
	# DO DEREGISTRATIONS
	do_deregistrations(registration_info_modulename)
	os.remove(registration_info_filename)
	
