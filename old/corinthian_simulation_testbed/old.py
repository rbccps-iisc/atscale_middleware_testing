#!/usr/bin/env python

import copy
import json
import math
import argparse
import random
import string
import argparse
import hashlib
import logging
import time
import sys
import warnings
import requests
import urllib3
import subprocess
from requests.adapters import HTTPAdapter
import multiprocessing as mp 

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

base_url = "https://localhost"

s = requests.Session();
s.mount('https://localhost/', HTTPAdapter(pool_connections=1))

output = mp.Queue()

colour ={}

colour['HEADER'] 		= '\033[95m'
colour['BLUE'] 			= '\033[94m'
colour['GREEN'] 		= '\033[92m'
colour['WARNING'] 		= '\033[93m'
colour['FAIL'] 			= '\033[91m'
colour['ENDC'] 			= '\033[0m'
colour['BOLD'] 			= '\033[1m'
colour['UNDERLINE'] 		= '\033[4m'
colour[''] 			= ''

def check(response, code):
	
	if response.status_code == code:
		return True
	else:
		return False

def register(ID, apikey, entity_id):
	
	url = base_url + "/register"
	headers = {"id": ID, "apikey": apikey, "entity": entity_id}
	r = s.post(url=url, headers=headers, data="{\"test\":\"schema\"}", verify=False)
	return r

def deregister(ID, apikey, entity_id):

	url = base_url + "/deregister"
	headers = {"id": ID, "apikey": apikey, "entity": entity_id}
	r = s.get(url=url, headers=headers, verify=False)
	return r

def publish(ID, apikey, to, topic, message_type, data):

	url = base_url + "/publish"
	headers = {"id": ID, "apikey": apikey, "to": to, "topic": topic, "message-type": message_type}
	r = s.post(url=url,headers=headers,data=data,verify=False)
	return r

def follow(ID, apikey, to_id, permission, from_id=""):

	url = base_url + "/follow"
	headers = {}

	if from_id:
		headers['from'] = from_id

	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to_id
	headers['topic'] = "test"
	headers['validity'] = "24"
	headers['permission'] = permission
	
	r = s.get(url=url,headers=headers,verify=False)
	return r

def share(ID, apikey, follow_id):

	url =base_url + "/share"
	headers = {"id": ID, "apikey": apikey, "follow-id": follow_id}
	r = s.get(url=url, headers=headers, verify=False)
	return r

def bind_unbind(ID, apikey, to, topic, req_type, from_id="", message_type=""):

	url = base_url
	headers = {}

	if req_type == "bind":
		url = url + "/bind"
	elif req_type == "unbind":
		url = url + "/unbind"

	if from_id:
		headers['from'] = from_id

	if message_type:
		headers['message-type'] = message_type

	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to
	headers['topic'] = topic

	r = s.get(url=url, headers=headers, verify=False)
	return r


def subscribe(ID, apikey, message_type="", num_messages=""):

	url = base_url + "/subscribe"
	headers = {}

	if message_type:
		headers['message-type'] = message_type

	if num_messages:
		headers['num-messages'] = num_messages

	headers['id'] = ID
	headers['apikey'] = apikey

	r = s.get(url=url, headers=headers, verify=False)
	return r

def follow_requests(ID, apikey, request_type):

	url = base_url

	if request_type == "requests":
		url = url + "/follow-requests"
	elif request_type == "status":
		url = url + "/follow-status"

	headers = {"id": ID, "apikey": apikey}

	r = s.get(url=url, headers=headers, verify=False)
	return r

def dev_publish(device_keys):
	for device, apikey in device_keys.items():
		logger.info("PUBLISHING MESSAGE FROM " + device)
		pub_req = publish(device, apikey, device, "test", "protected", "test message from " + device)
		pub_status = check(pub_req, 202)
		assert (pub_status)


def bind_unbind_dev(as_admin, req_type, expected, device_keys, app_keys):

	if as_admin == False:
		approved = 0
		for app, apikey in app_keys.items():
			logger.info("APP " + app + " CHECKING APPROVAL STATUS OF FOLLOW REQUESTS BEFORE BINDING")
			follow_status = follow_requests(app, apikey, "status")
			response = follow_status.json() 
			flag = check(follow_status, 200)

			for entry in response:
				if entry['status'] == "approved":
					approved = approved + 1

			assert (approved == expected)
			logger.info("APP " + app + " HAS RECEIVED " + str(approved) + " APPROVALS")
			approved = 0
		for app, apikey in app_keys.items():
			for device in device_keys:
				logger.info("APP " + app + " (UN)BINDING FROM DEVICE " + device)
				bind_req = bind_unbind(app, apikey, device, "test", req_type)
				bind_status = check(bind_req, 200)
				assert (bind_status)

	elif as_admin == True:

		approved = 0

		for app in app_keys:

			logger.info("APP " + app + " CHECKING APPROVAL STATUS OF FOLLOW REQUESTS BEFORE BINDING")
			follow_status = follow_requests("admin", "admin", "status")
			response = follow_status.json()

			flag = check(follow_status, 200)

			for entry in response:
				if entry['status'] == "approved":
					approved = approved + 1

			assert (approved == expected)
			logger.info("APP ADMIN HAS RECEIVED " + str(approved) + " APPROVALS")
			approved = 0

		for app in app_keys:
			for device in device_keys:
				logger.info("APP " + app + " BINDING TO DEVICE " + device)
				bind_req = bind_unbind("admin", "admin", device, "test", req_type, from_id=app)
				bind_status = check(bind_req, 200)
				assert (bind_status)


def app_subscribe(expected,app_keys, num_devices):

	count = math.ceil(num_devices / 10.0)

	actual = 0

	for app, apikey in app_keys.items():

		logger.info("APP " + app + " SUBSCRIBING TO ITS QUEUE")

		for i in range(0, int(count)):
			sub_req = subscribe(app, apikey, num_messages="10")
			response = sub_req.json() 
			actual = actual + len(response)
			sub_status = check(sub_req, 200)
			assert(sub_status)
		
		logger.info("APP " + app + " has successfully received " + str(actual) + " messages")


def follow_dev(as_admin, permission,device_keys, app_keys):
    if as_admin == True:
        for app in app_keys:
            for device in device_keys:
                logger.info("FOLLOW REQUEST FROM APP " + app + " TO DEVICE " + device)
                r = follow("admin", "admin", device, permission, from_id=app)
                follow_status = check(r, 202)
                if(not follow_status):
                    print("Response=",r.json())
                assert (follow_status)
            
    elif as_admin == False:
        for app, apikey in app_keys.items():
            for device in device_keys:
                logger.info("FOLLOW REQUEST FROM APP " + app + " TO DEVICE " + device)
                r = follow(app, apikey, device, permission)
                follow_status = check(r, 202)
                if(not follow_status):
                    print("Response=",r.json())
                assert (follow_status)
    

def share_dev(expected):

	r = follow_requests("admin", "admin", "requests")
	response = r.json() 
	count = 0

	assert(check(r,200))
	
	for follow_req in response:
		count = count + 1
		logger.info("SHARE FROM DEVICE " + str(follow_req['to']).split(".")[0] + " TO APP " + str(follow_req['from']))
		share_req = share("admin", "admin", str(follow_req['follow-id']))
		share_status = check(share_req, 200)
		assert (share_status)

	assert(count == expected)

def app_publish(expected_code,device_keys,app_keys):

	for app, apikey in app_keys.items():
		for device in device_keys:
			logger.info("APP "+ app +" PUBLISHING TO DEVICE "+ device +".command EXCHANGE")
			publish_req = publish(app,apikey, device, "test", "command", "data")
			assert(check(publish_req, expected_code))


def dev_subscribe(expected):

    num_apps = expected
    count = math.ceil(num_apps / 10.0)
    actual = 0
    
    for device, apikey in device_keys.items():
    
    	logger.info("DEVICE " + device + " SUBSCRIBING TO ITS COMMAND QUEUE")
    
    	for i in range(0, int(count)):
    		sub_req = subscribe(device, apikey, message_type="command", num_messages="10")
    		response = sub_req.json() 
    		actual = actual + len(response)
    		sub_status = check(sub_req, 200)
    		assert(sub_status)
    	
    	assert (actual == expected)
    	actual = 0
    	logger.info("DEVICE " + device + " HAS RECEIVED " + str(expected) + " COMMAND MESSAGES")


def do_registrations(num_devices, num_apps):
    
    device_keys ={}
    app_keys={}
    # Device regsitration
    logger.info(colour.HEADER + "---------------> REGISTERING DEVICES " + colour.ENDC)
    
    for i in range(num_devices):
    	dev_name = "dev" + str(i)
    	logger.info("REGISTERING DEVICE " + dev_name)
    	r = register('admin', 'admin', dev_name)
    	response = r.json()
    	logger.info(json.dumps(response))
    	reg_status = check(r, 200)
    	assert (reg_status)
    	device_keys[response['id']] = response['apikey']
    
    
    # App registration
    logger.info(colour.HEADER + "---------------> REGISTERING APPS" + colour.ENDC)
    
    for i in range(num_apps):
    	app_name = "app" + str(i)
    	logger.info("REGISTERING APP " + app_name)
    	r = register('admin', 'admin', app_name)
    	response = r.json()
    	logger.info(json.dumps(response))
    	reg_status = check(r, 200)
    	assert (reg_status)
    	app_keys[response['id']] = response['apikey']
    
    # save the device and app keys into files
    with open("device_keys.py", 'w') as f:
        f.write('device_keys = ')
        json.dump(device_keys, f)
    with open("app_keys.py", 'w') as f:
        f.write('app_keys = ')
        json.dump(app_keys, f)

def setup_permissions():
    
    from device_keys import device_keys
    from app_keys import app_keys
    
    #Apps request follow with read-write permissions
    logger.info(colour.HEADER+"---------------> APPS REQUEST FOLLOW WITH READ-WRITE PERMISSIONS"+colour.ENDC)
    follow_dev(as_admin=False, permission="read-write",device_keys=device_keys,app_keys=app_keys)
    time.sleep(1)
    
    #Devices approve issue share to apps
    logger.info(colour.HEADER+"---------------> DEVICES APPROVE READ-WRITE FOLLOW REQUESTS WITH SHARE"+colour.ENDC)
    share_dev(num_devices*num_apps*2)
    time.sleep(1)
    
    # Apps bind to devices' queues
    logger.info(colour.HEADER + "---------------> APPS BIND TO DEVICES" + colour.ENDC)
    bind_unbind_dev(as_admin=False, req_type="bind", expected=(2*num_devices),device_keys=device_keys,app_keys=app_keys)
    time.sleep(1)

def try_publish_subscribe(device_keys,app_keys):
    num_apps = len(app_keys)
    num_devices=len(device_keys)
    #Apps publish to command queue of devices
    logger.info(colour.HEADER+"---------------> APPS PUBLISH TO COMMAND EXCHANGE OF DEVICES"+colour.ENDC)
    app_publish(202,device_keys,app_keys)
    
    #Devices subscribe to their command queue
    logger.info(colour.HEADER+"---------------> DEVICES SUBSCRIBE TO THEIR COMMAND QUEUES"+colour.ENDC)
    dev_subscribe(num_apps)
    
    # Devices publish again
    logger.info(colour.HEADER + "---------------> DEVICES PUBLISH DATA" + colour.ENDC)
    dev_publish(device_keys)
    
    # Apps subscribe to messages
    logger.info(colour.HEADER + "---------------> APPS TRY TO READ PUBLISHED DATA" + colour.ENDC)
    app_subscribe(num_devices,app_keys, num_devices)

def do_deregistrations():
	
    from device_keys import device_keys
    from app_keys import app_keys
    
    #Deregister all apps and devices
    logger.info(colour.HEADER+"---------------> DEREGISTERING DEVICES AND APPS"+colour.ENDC)
    
    for device in device_keys:
    	logger.info("DEREGISTERING DEVICE "+ device +colour.ENDC)
    	dereg = deregister("admin","admin",device)
    	assert(check(dereg,200))
    
    for app in app_keys:
    	logger.info("DEREGISTERING APP "+ app +colour.ENDC)
    	dereg = deregister("admin","admin",app)
    	assert(check(dereg,200))
		
if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s %(levelname)-6s %(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # do registrations
    do_registrations(num_devices=1, num_apps=1)
    setup_permissions()
    
    # try publish/subscribe
    try_publish_subscribe(device_keys,app_keys)
    # do de-registrations
    do_deregistrations()
