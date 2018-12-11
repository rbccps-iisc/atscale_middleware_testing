#! python3
#
# Useful routines to register a bunch of entities with the middleware
# and setup the required permissions between them simply by reading a 
# python dictionary containing the system description.

# The system description consists of :
#   1. a list of unique device names
#	2. a list of unique app names
#   3. a list of permissions, where each permission is 
#      specified as (<app name>, <device name>, <permission, which can be"read"/"write">)
#
# This information is to be given as a python dictionary. For example:
#   system_description = {  "devices"       : [ "dev1", "dev2"],
#							"apps"			: [ "appA", "appB"],
#                           "permissions"   : [ ("appX","dev1","read"),("appX","dev1","write"),("appY","dev2","read")]
#                       }
#
# The routine returns True if there were no errors 
# and also returns a python dictionary containing the names of 
# the entities that were registered successfully and their corresponding apikeys.
#
# Optionally, if a file handle is passed as an argument,
# information about the registered entities is saved in this file.
#
#
# Author: Neha Karanjkar

from __future__ import print_function 
import corinthian_messaging
import logging
logger = logging.getLogger(__name__)
import json



def deregister_entities(list_of_entity_names):
	""" Takes a list of entity names and 
	deregisters them one-by-one.
	"""
	for entity in list_of_entity_names:
		# Admin prefix is not needed since the dict already contains prefixed entity names
		success = corinthian_messaging.deregister(entity)
		logger.info("DE-REGISTER: de-registering {} successful.".format(entity))


def register_entities(system_description, registration_info_file=None):
	""" routine to register a bunch of entities 
	and setup the required permissions between them.
	
	Arguments:
	    system_description: a python dictionary containing a list of unique device names,
						a list of unique app names and a list of permissions, where each permission is
	                    specified as (<app name>, <device name>, <permission>)
	                    where permission can be"read"/"write"/"read-write".
	                    
	    For example:
	    system_description = {  "devices"       : [ "dev1", "dev2"]
								"apps"			: [ "appX", "appY"],
	                           "permissions"   : [ ("appX","dev1","read"),("appX","dev1","write"),("appY","dev2","read")]
	                       }
	
	    registration_info_file (optional): Registration information is saved in this file.
	
	 Return Values:
	     The routines returns True if there were no errors 
	     and also returns a python dictionary containing the names of 
	     the entities that were registered successfully and their corresponding apikeys.
	 """
	registered_entities = {}
	logger.info("SETUP: setting up entities and permissions from system description:{}".format(system_description))
	
	try:
	
		devices = system_description["devices"]
		apps	= system_description["apps"]
		entities = devices+apps
		permissions = system_description["permissions"]
		
		# check if all entity names are sane.
		for name in entities:
			if not (all(c.isdigit() or c.islower() for c in name)):
				logger.error("Illegal entity name:{}".format(name))
				logger.error("Entity names can only contain lowercase letters and numbers.")
				assert(False),"Illegal entity name"
		
		# check if all permissions are sane
		for p in permissions:
			assert(len(p)==3)
			app = p[0]
			dev = p[1]
			permission = p[2]
			
			assert(app in apps)
			assert(dev in devices)
			assert(permission=="read" or permission=="write" or permission=="read-write")
		
		
		# Now register all entities:
		for i in entities:
			apikey = corinthian_messaging.register(i)
			logger.info("REGISTER: registering entity {} successful. apikey ={} ".format(i,apikey))
			registered_entities["admin/"+i]=apikey
				
		# Set up permissions one-by-one
		logger.info("SETUP: setting up permissions between entities...")
		for p in permissions:
			app = p[0]
			target_device = p[1]
			permission = p[2]
			
			app_apikey = registered_entities["admin/"+app]
			target_device_apikey = registered_entities["admin/"+target_device]
			
			# send a follow request
			success = corinthian_messaging.follow("admin/"+app, app_apikey, "admin/"+target_device, permission)
			logger.debug("FOLLOW: {} sent a follow request to {} for permission {}".format(app, target_device, permission))
			
			# get the target_device to check the follow request
			messages = corinthian_messaging.follow_requests("admin/"+target_device, target_device_apikey,"requests")
			follow_list = []
			if permission == "read" or permission == "write":
				follow_list.append(messages.json()[0]["follow-id"])
			elif permission == "read-write":
				follow_list.append(messages.json()[0]["follow-id"])
				follow_list.append(messages.json()[1]["follow-id"])
			logger.debug("FOLLOW: {} received a follow request from {} for permission {}".format(target_device,app, permission))
			# get the target entitity to approve the follow request using "share" 
			for follow_id in follow_list:
				success = corinthian_messaging.share("admin/"+target_device,target_device_apikey, follow_id)
			logger.debug("SHARE: {} sent a share request for entity {} for permission {}".format(target_device, app, permission))
			# get the app to check for the follow notification
			follow_status_response = corinthian_messaging.follow_requests("admin/"+app, app_apikey, "status")
			statuses = follow_status_response.json()
			for status in statuses:
				assert(status["status"] == "approved")
			logger.debug("FOLLOW: follow request made by {} was approved.".format(app))
			if permission == "read" or permission == "read-write":
				# get the app to bind to the target entity's protected stream
				success = corinthian_messaging.bind_unbind("admin/"+app, app_apikey, "admin/"+target_device, "#", "protected")
				logger.debug("BIND: {} sent a bind request for {} .".format(app, target_device))
		
		# setup done!
		logger.info("SETUP: done.")
		# write out the registration info in a file.
		if(registration_info_file):
			logger.info("SETUP: writing info about registered entities into file")
			devices = ["admin/"+str(i) for i in devices]
			apps = ["admin/"+str(i) for i in apps]
			registration_info_file.write("\nsystem_description= %s"%system_description)
			registration_info_file.write("\ndevices= %s"%devices)
			registration_info_file.write("\napps= %s"%apps)
			registration_info_file.write("\nregistered_entities= %s"%registered_entities)
		
		return True, registered_entities
	
	except:
		logger.error("An exception occurred during setup. Deregistering all entities.") 
		deregister_entities(registered_entities)
		raise




# Testbench:
if __name__=='__main__':
    
	# logging settings:
	logging.basicConfig(level=logging.DEBUG)
	
	# suppress debug messages from other modules used.
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("corinthian_messaging").setLevel(logging.WARNING)
	
	
	# register devices and apps and set up permissions
	devices = ["device"+str(i) for i in range(2)]
	apps = ["app"+str(i) for i in range (1)]
	
	system_description = {  "devices"       : devices,
							"apps"			: apps,
	                        "permissions"   : [ (a,d,"read-write") for a in apps for d in devices ]
	                    }
	with open("registration_info.py", "w+") as f:
		success, registered_entities = register_entities(system_description,f)
	
	# check if publish/subscribe works
	if(success):
		dev = "admin/"+str(devices[0])
		ap = "admin/"+str(apps[0])
		dev_apikey = registered_entities[dev]
		ap_apikey =  registered_entities[ap]

		# Get dev to publish some stuff.
		for i in range (10):
			data = "DUMMY_DATA_"+str(i)
			print("PUBLISH: Publishing from device",dev," Data=",data)
			success = corinthian_messaging.publish(dev,dev_apikey, dev, "#", "protected", json.dumps(data))
			
		# Get ap to print the data it has susbscribed to
		messages = corinthian_messaging.subscribe(ap, ap_apikey)
		print ("SUBSCRIBE: ",ap," received the following data from ",dev,":")
		for m in messages.json():
			print(m)

		# deregister the entities
		deregister_entities(registered_entities)
