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
s.mount('https://localhost/', HTTPAdapter(pool_connections=100))

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


# generate an admin user
def gen_admin():
    
    admin_id = gen_rand(8)
    apikey = gen_rand(32)
    salt = gen_rand(32)
    string = apikey + salt + admin_id
    hash_string = hashlib.sha256(string.encode()).hexdigest()
    cmd = "docker exec postgres psql -U postgres -c \"insert into users values('"+admin_id+"','"+hash_string+"',NULL,'"+salt+"','f','t') ON CONFLICT DO NOTHING\""
    try:
        p = subprocess.check_output(cmd, shell=True)
    except Exception as e:
        print("Could not create admin user")
        sys.exit(1)
    return admin_id, apikey


def log(message, clr, modifier=""):

	if clr:
		logger.info(colour[clr]+colour[modifier]+message+colour['ENDC'])
	else:
		logger.info(message)

def check(response, code):
	
	assert(response.status_code == code), "Message = "+response.text+" Status code = "+str(response.status_code)

def gen_rand(size, prefix=""):

	rand_str = prefix + ''.join(random.choice(string.ascii_lowercase) for _ in range(size))
	return rand_str

def get_entity(device_keys, app_keys, entity_type=""):

    if entity_type == "dev":
	    name = random.choice(device_keys.keys())
	    key = str(device_keys[name])
    elif entity_type == "app":
	    name = random.choice(app_keys.keys())
	    key = str(app_keys[name])
	    
    return name, key

def register_owner(ID, apikey, owner):
	
	url = base_url + "/register-owner"
	headers = {"id": ID, "apikey": apikey, "owner": owner}
	r = s.post(url=url, headers=headers, verify=False)
	return r

def register(ID, apikey, entity_id):
	
	url = base_url + "/register"
	headers = {"id": ID, "apikey": apikey, "entity": entity_id, "is-autonomous": "true"}
	r = s.post(url=url, headers=headers, data="{\"test\":\"schema\"}", verify=False)
	return r

def deregister(ID, apikey, entity_id):

	url = base_url + "/deregister"
	headers = {"id": ID, "apikey": apikey, "entity": entity_id}
	r = s.get(url=url, headers=headers, verify=False)
	return r

def block_unblock(ID, apikey, entity_id, req_type):
	
	url = base_url 
	
	if req_type == "block":
		url = url + "/block"
	elif req_type == "unblock":
		url = url + "/unblock"

	headers = {"id": ID, "apikey": apikey, "entity": entity_id}
	r = s.get(url=url, headers=headers, verify=False)
	return r

def permissions(ID, apikey, entity_id=""):

	url = base_url + "/permissions"

	headers = {}

	if entity_id:
		headers['entity'] = entity_id

	headers ['id'] 		= ID
	headers	['apikey'] 	= apikey

	r = s.get(url=url, headers=headers, verify=False)
	return r

def publish(ID, apikey, to, topic, message_type, data):

	url = base_url + "/publish"
	headers = {"id": ID, "apikey": apikey, "to": to, "subject": topic, "message-type": message_type, "content-type": "text/plain"}
	r = s.post(url=url,headers=headers,data=data,verify=False)
	return r

def follow(ID, apikey, to_id, permission, from_id="", topic ="", validity = "", message_type=""):

	url = base_url + "/follow"
	headers = {}

	if from_id:
		headers['from'] = from_id

	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to_id

	if topic:
	    headers['topic'] = topic
	else:
	    headers['topic'] = "test"

	if validity:
	    headers['validity'] = validity
	else:
	    headers['validity'] = "24"

	if message_type:
	    headers['message-type'] = message_type

	headers['permission'] = permission
	
	r = s.get(url=url,headers=headers,verify=False)
	return r

def reject_follow(ID, apikey, follow_id):
	
	url =base_url + "/reject-follow"
	headers = {"id": ID, "apikey": apikey, "follow-id": follow_id}
	r = s.get(url=url, headers=headers, verify=False)
	return r
	

def unfollow(ID, apikey, to, topic, permission, message_type, from_id=""):

	url = base_url + "/unfollow"
	headers = {}

	if from_id:
		headers['from'] = from_id

	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to
	headers['topic'] = "test"
	headers['permission'] = permission
	headers['message-type'] = message_type 
	
	r = s.get(url=url,headers=headers,verify=False)
	return r

def share(ID, apikey, follow_id):

	url =base_url + "/share"
	headers = {"id": ID, "apikey": apikey, "follow-id": follow_id}
	r = s.get(url=url, headers=headers, verify=False)
	return r

def bind_unbind(ID, apikey, to, topic, req_type, message_type, from_id="", is_priority="false"):

	url = base_url
	headers = {}

	if req_type == "bind":
		url = url + "/bind"
	elif req_type == "unbind":
		url = url + "/unbind"

	if from_id:
		headers['from'] = from_id

	headers['message-type'] = message_type

	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to
	headers['topic'] = topic
	headers['is-priority'] = is_priority 

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

def dev_publish(device_keys, message_type="protected"):

	for device, apikey in device_keys.items():
		log("PUBLISHING MESSAGE FROM " + device,'')
		pub_req = publish(device, apikey, device, "test", message_type, "test message from " + device)
		check(pub_req, 202)

def bind_unbind_dev(device_keys, app_keys, expected=0, as_admin="", req_type="",
message_type="protected", is_priority="false", admin_id="", admin_key=""):

	if as_admin == False:

		approved = 0

		for app, apikey in app_keys.items():
			log("APP " + app + " CHECKING APPROVAL STATUS OF FOLLOW REQUESTS BEFORE BINDING",'')
			follow_status = follow_requests(app, apikey, "status")
			response = follow_status.json() 
			check(follow_status, 200)

			for entry in response:
				if entry['status'] == "approved":
					approved = approved + 1

			assert (approved == expected)
			log("APP " + app + " HAS RECEIVED " + str(approved) + " APPROVALS",'')
			approved = 0

		for app, apikey in app_keys.items():
			for device in device_keys:
				log("APP " + app + " (UN)BINDING FROM DEVICE " + device,'')
				bind_req = bind_unbind(app, apikey, device, "test", req_type,
				message_type, is_priority=is_priority)
				check(bind_req, 200)

	elif as_admin == True:

		approved = 0

		for app in app_keys:

			log("APP " + app + " CHECKING APPROVAL STATUS OF FOLLOW REQUESTS BEFORE BINDING",'')
			follow_status = follow_requests(admin_id, admin_key, "status")
			response = follow_status.json()

			check(follow_status, 200)

			for entry in response:
				if entry['status'] == "approved":
					approved = approved + 1

			assert (approved == expected)
			log("APP ADMIN HAS RECEIVED " + str(approved) + " APPROVALS",'')
			approved = 0

		for app in app_keys:
			for device in device_keys:
				log("APP " + app + " BINDING TO DEVICE " + device,'')
				bind_req = bind_unbind(admin_id, admin_key, device, "test", req_type,
				message_type, from_id=app, is_priority=is_priority)
				check(bind_req, 200)


def bind_unbind_without_follow(device_keys, app_keys, as_admin="", req_type="",
message_type="protected", is_priority = "false", admin_id="", admin_key=""):

	if as_admin == False:
			for app, apikey in app_keys.items():
					for device in device_keys:
						log("APP " + app + " (UN)BINDING FROM DEVICE " + device,'')
						bind_req = bind_unbind(app, apikey, device, "test",
						req_type, message_type, is_priority = is_priority)
						check(bind_req, 403)

	elif as_admin == True:
		for app in app_keys:
			for device in device_keys:
				log("APP " + app + " BINDING TO DEVICE " + device,'')
				bind_req = bind_unbind(admin_id, admin_key, device, "test", req_type,
				message_type, from_id=app, is_priority=is_priority)
				check(bind_req, 403)

def app_subscribe(devices, app_keys, expected, message_type=""):

	count = math.ceil(devices / 10.0)

	actual = 0

	for app, apikey in app_keys.items():

		log("APP " + app + " SUBSCRIBING TO ITS QUEUE",'')

		for i in range(0, int(count)):
			
			if message_type:
			    sub_req = subscribe(app, apikey, num_messages="10",
			    message_type=message_type)
			else:
			    sub_req = subscribe(app, apikey, num_messages="10")

			response = sub_req.json() 
			actual = actual + len(response)
			check(sub_req, 200)
		
		assert (actual == expected)
		actual = 0
		log("APP " + app + " has successfully received " + str(expected) + " messages",'')


def follow_dev(device_keys, app_keys, as_admin="", permission="", message_type="protected",
admin_id="", admin_key=""):

	if as_admin == True:
		for app in app_keys:
			for device in device_keys:
				log("FOLLOW REQUEST FROM APP " + app + " TO DEVICE " + device,'')
				r = follow(admin_id, admin_key, device, permission, from_id=app,
				message_type=message_type)
				check(r, 202)

	elif as_admin == False:
		for app, apikey in app_keys.items():
			for device in device_keys:
				log("FOLLOW REQUEST FROM APP " + app + " TO DEVICE " + device,'')
				r = follow(app, apikey, device, permission,
				message_type=message_type)
				check(r, 202)

def unfollow_dev(device_keys, app_keys, as_admin="", permission="", message_type = "protected",
admin_id="", admin_key=""):

	if as_admin == True:
		for app in app_keys:
			for device in device_keys:
				log("UNFOLLOW REQUEST FROM APP " + app + " TO DEVICE " + device,'')
				r = unfollow(admin_id, admin_key, device, "test", permission,
				message_type, from_id=app)
				check(r, 200)

	elif as_admin == False:
		for app, apikey in app_keys.items():
			for device in device_keys:
				log("UNFOLLOW REQUEST FROM APP " + app + " TO DEVICE " + device,'')
				r = unfollow(app, apikey, device, "test", permission, message_type)
				check(r, 200)

def share_dev(expected, admin_id, admin_key):

	r = follow_requests(admin_id, admin_key, "requests")
	response = r.json() 
	count = 0

	check(r,200)
	
	for follow_req in response:
		count = count + 1
		log("SHARE FROM DEVICE " + str(follow_req['to']).split(".")[0] + " TO APP " + str(follow_req['from']),'')
		share_req = share(admin_id, admin_key, str(follow_req['follow-id']))
		check(share_req, 200)

	assert(count == expected)

def app_publish(device_keys, app_keys, expected_code):

	for app, apikey in app_keys.items():
		for device in device_keys:
			log("APP "+ app +" PUBLISHING TO DEVICE "+ device +".command EXCHANGE",'')
			publish_req = publish(app,apikey, device, "test", "command", "data")

			check(publish_req, expected_code)


def dev_subscribe(apps, device_keys, expected):

	count = math.ceil(apps / 10.0)

	actual = 0

	for device, apikey in device_keys.items():

		log("DEVICE " + device + " SUBSCRIBING TO ITS COMMAND QUEUE",'')

		for i in range(0, int(count)):
			sub_req = subscribe(device, apikey, message_type="command", num_messages="10")
			response = sub_req.json() 
			actual = actual + len(response)
			check(sub_req, 200)
		
		assert (actual == expected)
		actual = 0
		log("DEVICE " + device + " HAS RECEIVED " + str(expected) + " COMMAND MESSAGES",'')

def registrations(devices, apps, dev_admin_id, dev_admin_key, app_admin_id, app_admin_key):
    device_keys = {}
    app_keys = {}
    
    # Device regsitration
    log("---------------> REGISTERING DEVICES ",'HEADER')
    for i in range(0, devices):
        log("REGISTERING DEVICE " + str(i),'')
        dev_name = "dev" + str(i)
        r = register(dev_admin_id, dev_admin_key, dev_name)
        response = r.json()
        log(json.dumps(response),'')
        check(r, 201)
        device_keys[response['id']] = response['apikey']
    
    # App registration
	log("---------------> REGISTERING APPS", 'HEADER')

	for i in range(0, apps):
		log("REGISTERING APP " + str(i),'')
		app_name = "app" + ''.join(
			random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(8))
		r = register(app_admin_id, app_admin_key, app_name)
		response = r.json()
		log(json.dumps(response),'')
		check(r, 201)

		app_keys[response['id']] = response['apikey']

	return device_keys, app_keys

def deregistrations(device_keys, app_keys, dev_admin_id, dev_admin_key, app_admin_id, app_admin_key):

	#Deregister all apps and devices
	log("---------------> DEREGISTERING DEVICES AND APPS",'HEADER')

	for device in device_keys:
		log("DEREGISTERING DEVICE "+ device,'')
		dereg = deregister(dev_admin_id, dev_admin_key,device)
		check(dereg,200)
 
	for app in app_keys:
		log("DEREGISTERING APP "+ app,'')
		dereg = deregister(app_admin_id, app_admin_key, app)
		check(dereg,200)

def security_tests():

	print("\n\n")
	log("========================= SECURITY TESTS =========================\n\n", 'GREEN', modifier='BOLD')
	
	dummy_key = gen_rand(32) 
	dummy_id  = gen_rand(8) 

	devices = random.randint(2,5)
	apps 	= random.randint(2,5)

	dev_admin_id, dev_admin_key = gen_admin()
	app_admin_id, app_admin_key = gen_admin()

	reg_time = time.time()
	device_keys, app_keys = registrations(devices, apps, dev_admin_id, dev_admin_key,
	app_admin_id, app_admin_key)	
	reg_time = time.time() - reg_time

	#Trying to register an owner from outside the localhost
	
	#logger.info(colour.HEADER + "---------------> OWNER REGISTRATION FROM OUTSIDE LOCALHOST " + colour.ENDC)

	#r = register_owner("admin", admin_key, "owner"+dummy_id)
	#check(r,403)
	#logger.info("Received 403: OK")

	test_time = time.time()
	#=========================================Invalid API key===============================================
	print("\n\n")
	log("------------------------- INVALID APIKEY -------------------------\n\n", 'GREEN')

	#Owner registration ( should not go through with the right apikey anyway ) 
	
	#logger.info(colour.HEADER + "---------------> OWNER REGISTRATION USING INVALID APIKEY " + colour.ENDC)
	#r = register_owner("admin", dummy_key, "owner"+dummy_id)
	#check(r,403)
	#logger.info("Received 403: OK")

	#Registration
	log("---------------> REGISTRATION USING INVALID APIKEY", 'HEADER')
	
	r = register(dev_admin_id, dummy_key, "dev"+dummy_id)
	check(r,403)
	log("Received 403: OK",'')

	#Publish
	log("---------------> PUBLISH USING INVALID APIKEY", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, dummy_key, dev_name, "test", "protected", "hello")
	check(r,403)
	log("Received 403: OK",'')

	log("---------------> PUBLISH USING VALID APIKEY TO ESTABLISH CONNECTION", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, str(device_keys[dev_name]), dev_name, "test", "protected", "hello")
	check(r,202)
	log("Received 202: OK",'')

	log("---------------> PUBLISH USING INVALID APIKEY ONCE CONNECTION HAS BEEN ESTABLISHED", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, dummy_key, dev_name, "test", "protected", "hello")
	check(r,403)
	log("Received 403: OK",'')

	#Subscribe
	log("---------------> SUBSCRIBE USING INVALID APIKEY", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = subscribe(dev_name, dummy_key)
	check(r,403)
	log("Received 403: OK",'')

	#Follow
	log("---------------> FOLLOW USING INVALID APIKEY", 'HEADER')

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	r = follow(app_name, dummy_key, random.choice(device_keys.keys()), "read")
	check(r,403)
	log("Received 403: OK",'')
	
	#Follow using invalid admin key
	log("---------------> FOLLOW USING INVALID ADMIN APIKEY", 'HEADER')

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = follow(app_admin_id, dummy_key, random.choice(device_keys.keys()), "read")
	check(r,403)
	log("Received 403: OK",'')

	#Share
	log("---------------> SHARE USING INVALID APIKEY", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = share(dev_name, dummy_key, str(random.randint(0,5)))
	check(r,403)
	log("Received 403: OK",'')
	
	#Share using invalid admin key
	log("---------------> SHARE USING INVALID ADMIN APIKEY", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = share(dev_admin_id, dummy_key, str(random.randint(0,5)))
	check(r,403)
	log("Received 403: OK",'')

	#Unfollow
	log("---------------> UNFOLLOW USING INVALID APIKEY", 'HEADER')
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = unfollow(app_name, dummy_key, str(random.choice(device_keys.keys())), "test", "read", "protected")
	check(r,403)
	log("Received 403: OK",'')

	#Unfollow using invalid admin apikey
	log("---------------> UNFOLLOW USING INVALID ADMIN APIKEY", 'HEADER')
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = unfollow(app_admin_id, dummy_key, str(random.choice(device_keys.keys())), "test", "read", "protected", from_id=app_name)
	check(r,403)
	log("Received 403: OK",'')

	#Follow-requests
	log("---------------> FOLLOW-REQUESTS USING INVALID APIKEY", 'HEADER')

	r = follow_requests(dev_admin_id, dummy_key, "requests")
	check(r,403)
	log("Received 403: OK",'')
	
	#Follow-requests using invalid device apikey
	log("---------------> FOLLOW-REQUESTS USING INVALID DEVICE APIKEY", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow_requests(dev_name, dummy_key, "requests")
	check(r,403)
	log("Received 403: OK",'')

	#Follow-status
	log("---------------> FOLLOW-STATUS USING INVALID APIKEY", 'HEADER')

	r = follow_requests(dev_admin_id, dummy_key, "status")
	check(r,403)
	log("Received 403: OK",'')

	#Follow-status using invalid device apikey
	log("---------------> FOLLOW-STATUS USING INVALID DEVICE APIKEY", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow_requests(dev_name, dummy_key, "status")
	check(r,403)
	log("Received 403: OK",'')

	#Reject follow using invalid admin key
	log("---------------> REJECT-FOLLOW USING INVALID ADMIN APIKEY", 'HEADER')

	r = reject_follow(dev_admin_id, dummy_key, str(random.randint(1,5)))
	check(r,403)
	log("Received 403: OK",'')
		
	#Reject follow using invalid device key
	log("---------------> REJECT-FOLLOW USING INVALID DEVICE APIKEY", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = reject_follow(dev_name, dummy_key, str(random.randint(1,5)))
	check(r,403)
	log("Received 403: OK",'')

	#Bind using invalid device apikey
	log("---------------> BIND USING INVALID DEVICE APIKEY", 'HEADER')

	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(app_name, dummy_key, dev_name, "test", "bind", "protected")
	check(r,403)
	log("Received 403: OK",'')
	
	#Bind using invalid admin apikey
	log("---------------> BIND USING INVALID ADMIN APIKEY", 'HEADER')

	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = bind_unbind(app_admin_id, dummy_key, dev_name, "test", "bind", "protected", from_id = app_name)
	check(r,403)
	log("Received 403: OK",'')

	#Unbind using invalid device apikey
	log("---------------> UNBIND USING INVALID DEVICE APIKEY", 'HEADER')

	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(app_name, dummy_key, dev_name, "test", "unbind", "protected")
	check(r,403)
	log("Received 403: OK",'')
	
	#Bind using invalid admin apikey
	log("---------------> UNBIND USING INVALID ADMIN APIKEY", 'HEADER')

	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(app_admin_id, dummy_key, dev_name, "test", "unbind", "protected", from_id = app_name)
	check(r,403)
	log("Received 403: OK",'')

	#Block using invalid admin apikey	
	log("---------------> BLOCK USING INVALID ADMIN APIKEY", 'HEADER')

	r = block_unblock(dev_admin_id, dummy_key, str(random.choice(app_keys.keys())), "block")
	check(r,403)
	log("Received 403: OK",'')

	#Unblock using invalid admin apikey	
	log("---------------> UNBLOCK USING INVALID ADMIN APIKEY", 'HEADER')

	r = block_unblock(dev_admin_id, dummy_key, str(random.choice(app_keys.keys())), "unblock")
	check(r,403)
	log("Received 403: OK",'')

	#Permissions using invalid admin apikey
	log("---------------> PERMISSIONS USING INVALID ADMIN APIKEY", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = permissions(dev_admin_id, dummy_key, entity_id = dev_name)
	check(r,403)
	log("Received 403: OK",'')
	
	#Permissions using invalid device apikey
	log("---------------> PERMISSIONS USING INVALID DEVICE APIKEY", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = permissions(dev_name, dummy_key)
	check(r,403)
	log("Received 403: OK",'')

	#Deregister using invalid apikey
	
	log("---------------> DEREGISTRATION USING INVALID ADMIN APIKEY", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = deregister(dev_admin_id, dummy_key, dev_name)
	check(r,403)
	log("Received 403: OK",'')

	#=========================================Invalid ID===============================================
	
	dummy_key = gen_rand(32) 
	dummy_id  = gen_rand(8, prefix="admin/") 
	dummy_admin_id = gen_rand(8) 

	print("\n\n")
	log("------------------------- INVALID ID -------------------------\n\n", 'GREEN')

	#Owner registration ( should not go through with the right apikey anyway ) 
	
	#logger.info(colour.HEADER + "---------------> OWNER REGISTRATION USING INVALID APIKEY " + colour.ENDC)
	#r = register_owner("admin", dummy_key, "owner"+dummy_id)
	#check(r,403)
	#logger.info("Received 403: OK")

	#Registration
	log("---------------> REGISTRATION USING INVALID ID", 'HEADER')
	
	r = register(dummy_id, dev_admin_key, "dev"+dummy_id)
	check(r,403)
	log("Received 403: OK",'')

	#Publish
	log("---------------> PUBLISH USING INVALID ID", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dummy_id, str(device_keys[dev_name]), dummy_id, "test", "protected", "hello")
	check(r,403)
	log("Received 403: OK",'')

	log("---------------> PUBLISH USING VALID APIKEY AND ID TO ESTABLISH CONNECTION", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, str(device_keys[dev_name]), dev_name, "test", "protected", "hello")
	check(r,202)
	log("Received 202: OK",'')

	log("---------------> PUBLISH USING INVALID ID ONCE CONNECTION HAS BEEN ESTABLISHED", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dummy_id, str(device_keys[dev_name]), dummy_id , "test", "protected", "hello")
	check(r,403)
	log("Received 403: OK",'')

	#Subscribe
	log("---------------> SUBSCRIBE USING INVALID ID", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = subscribe(dummy_id, str(device_keys[dev_name]))
	check(r,403)
	log("Received 403: OK",'')

	#Follow
	log("---------------> FOLLOW USING INVALID ID", 'HEADER')

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = follow(dummy_id, str(app_keys[app_name]), random.choice(device_keys.keys()), "read")
	check(r,403)
	log("Received 403: OK",'')
	
	#Follow using invalid admin id
	log("---------------> FOLLOW USING INVALID ADMIN ID", 'HEADER')

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = follow(dummy_id, app_admin_key, random.choice(device_keys.keys()), "read")
	check(r,403)
	log("Received 403: OK",'')

	#Share
	log("---------------> SHARE USING INVALID ID", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = share(dummy_id, str(device_keys[dev_name]), str(random.randint(0,5)))
	check(r,403)
	log("Received 403: OK",'')
	
	#Share using invalid admin id
	log("---------------> SHARE USING INVALID ADMIN ID", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = share(dummy_id, dev_admin_key, str(random.randint(0,5)))
	check(r,403)
	log("Received 403: OK",'')

	#Unfollow
	log("---------------> UNFOLLOW USING INVALID ID", 'HEADER')
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = unfollow(dummy_id, str(app_keys[app_name]), str(random.choice(device_keys.keys())), "test", "read", "protected")
	check(r,403)
	log("Received 403: OK",'')

	#Unfollow using invalid admin id
	log("---------------> UNFOLLOW USING INVALID ADMIN ID", 'HEADER')
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = unfollow(dummy_id, app_admin_key, str(random.choice(device_keys.keys())), "test", "read", "protected", from_id=app_name)
	check(r,403)
	log("Received 403: OK",'')

	#Follow-requests
	log("---------------> FOLLOW-REQUESTS USING INVALID ID", 'HEADER')

	r = follow_requests(dummy_id, dev_admin_key, "requests")
	check(r,403)
	log("Received 403: OK",'')
	
	#Follow-requests using invalid device id
	log("---------------> FOLLOW-REQUESTS USING INVALID DEVICE ID", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow_requests(dummy_id, str(device_keys[dev_name]), "requests")
	check(r,403)
	log("Received 403: OK",'')

	#Follow-status
	log("---------------> FOLLOW-STATUS USING INVALID ID", 'HEADER')

	r = follow_requests(dummy_id, app_admin_key , "status")
	check(r,403)
	log("Received 403: OK",'')

	#Follow-status using invalid device id
	log("---------------> FOLLOW-STATUS USING INVALID DEVICE ID", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow_requests(dummy_id, str(device_keys[dev_name]), "status")
	check(r,403)
	log("Received 403: OK",'')

	#Reject follow using invalid admin id
	log("---------------> REJECT-FOLLOW USING INVALID ADMIN ID", 'HEADER')

	r = reject_follow(dummy_id, dev_admin_key, str(random.randint(1,5)))
	check(r,403)
	log("Received 403: OK",'')
		
	#Reject follow using invalid device id
	log("---------------> REJECT-FOLLOW USING INVALID DEVICE ID", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = reject_follow(dummy_id, str(device_keys[dev_name]), str(random.randint(1,5)))
	check(r,403)
	log("Received 403: OK",'')

	#Bind using invalid device id
	log("---------------> BIND USING INVALID DEVICE ID", 'HEADER')

	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(dummy_id, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r,403)
	log("Received 403: OK",'')
	
	#Bind using invalid admin id
	log("---------------> BIND USING INVALID ADMIN ID", 'HEADER')

	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(dummy_id, app_admin_key, dev_name, "test", "bind", "protected", from_id = app_name)
	check(r,403)
	log("Received 403: OK",'')

	#Unbind using invalid device id
	log("---------------> UNBIND USING INVALID DEVICE ID", 'HEADER')

	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = bind_unbind(dummy_id, str(app_keys[app_name]), dev_name, "test", "unbind", "protected")
	check(r,403)
	log("Received 403: OK",'')
	
	#Bind using invalid admin idy
	log("---------------> UNBIND USING INVALID ADMIN ID", 'HEADER')

	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = bind_unbind(dummy_id, app_admin_key, dev_name, "test", "unbind", "protected", from_id = app_name)
	check(r,403)
	log("Received 403: OK",'')

	#Block using invalid admin id	
	log("---------------> BLOCK USING INVALID ADMIN ID", 'HEADER')

	r = block_unblock(dummy_admin_id, dev_admin_key, str(random.choice(device_keys.keys())), "block")
	check(r,403)
	log("Received 403: OK",'')

	#Unblock using invalid admin id	
	log("---------------> UNBLOCK USING INVALID ADMIN ID", 'HEADER')

	r = block_unblock(dummy_admin_id, dev_admin_key, str(random.choice(device_keys.keys())), "unblock")
	check(r,403)
	log("Received 403: OK",'')

	#Permissions using invalid admin id
	log("---------------> PERMISSIONS USING INVALID ADMIN ID", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = permissions(dummy_admin_id, dev_admin_key, entity_id = dev_name)
	check(r,403)
	log("Received 403: OK",'')
	
	#Permissions using invalid device id
	log("---------------> PERMISSIONS USING INVALID DEVICE ID", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = permissions(dummy_id, str(device_keys[dev_name]))
	check(r,403)
	log("Received 403: OK",'')

	#Deregister using invalid id
	
	log("---------------> DEREGISTRATION USING INVALID ADMIN ID", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = deregister(dummy_id, dev_admin_key, dev_name)
	check(r,403)
	log("Received 403: OK",'')

	print("\n\n")
	log("------------------------- PUBLISH -------------------------\n\n", 'GREEN')

	#Publish to non-existent exchange
	log("---------------> PUBLISH TO NON-EXISTENT EXCHANGE", 'HEADER')

	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	dummy_exchange = gen_rand(8, prefix = gen_rand(8)+"/") 
	r = publish(dev_name, dev_key, dummy_exchange, "test", "command", "hello") 
	check(r,202)
	log("Received 202: OK",'')

	#Publish without authroisation
	log("---------------> PUBLISH WITHOUT AUTHORISATION", 'HEADER')


	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(app_name, str(app_keys[app_name]), dev_name, "test", "command", "hello") 
	check(r,202)
	log("Received 202: OK",'')

	#Publish to amq.topic
	log("---------------> PUBLISH TO amq.topic", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, str(device_keys[dev_name]), "amq.topic", "test", "command", "hello") 
	check(r,400)
	log("Received 400: OK",'')

	#Publish to amq.direct
	log("---------------> PUBLISH TO amq.direct", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, str(device_keys[dev_name]), "amq.direct", "test", "command", "hello") 
	check(r,400)
	log("Received 400: OK",'')

	#Publish to amq.headers
	log("---------------> PUBLISH TO amq.headers", 'HEADER')
	
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, str(device_keys[dev_name]), "amq.headers", "test", "command", "hello") 
	check(r,400)
	log("Received 400: OK",'')

	#Publish to amq.fanout
	log("---------------> PUBLISH TO amq.fanout", 'HEADER')

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, str(device_keys[dev_name]), "amq.fanout", "test", "command", "hello") 
	check(r,400)
	log("Received 400: OK",'')

	#Publish with invalid message-type
	log("---------------> PUBLISH WITH INVALID MESSAGE-TYPE", 'HEADER')
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = publish(dev_name, str(device_keys[dev_name]), dev_name, "test", gen_rand(8), "hello") 
	check(r,400)
	log("Received 400: OK",'')

	print("\n\n")
	log("------------------------- SUBSCRIBE -------------------------\n\n", 'GREEN')

	#With invalid message type

	log("---------------> SUBSCRIBE WITH INVALID MESSAGE-TYPE", 'HEADER') 
	dummy_mt = gen_rand(8)


	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = subscribe(app_name, app_key, dummy_mt)
	check(r,400)
	log("Received 400: OK",'')

	#With invalid num messages 

	log("---------------> SUBSCRIBE WITH INVALID NUM MESSSAGES", 'HEADER') 
	dummy_nm = gen_rand(8)

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = subscribe(app_name, app_key, num_messages= dummy_nm)
	check(r,400)
	log("Received 400: OK ",'')

	print("\n\n")
	log("------------------------- BIND -------------------------\n\n", 'GREEN')

	#Bind to unauthorised exchange
	log("---------------> BIND TO UNAUTHORISED EXCHANGE", 'HEADER') 

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 403)
	log("Received 403: OK",'')
		
	#Bind to non-existent exchange
	log("---------------> BIND TO NON-EXISTENT EXCHANGE", 'HEADER') 

	dummy_exchange = gen_rand(8, prefix= gen_rand(8))
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(app_name, str(app_keys[app_name]), dummy_exchange, "test", "bind", "protected")
	check(r, 403)
	log("Received 403: OK",'')
	
	#Bind using invalid message_type
	log("---------------> BIND USING INVALID MESSAGE-TYPE", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, str(device_keys[dev_name]), follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", gen_rand(8))
	check(r, 400)
	log("Received 400: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)
	
	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Bind with a different topic from what was requested in follow 
	log("---------------> BIND USING UNAUTHORISED TOPIC", 'HEADER') 


	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, str(device_keys[dev_name]), follow_id)
	check(r, 200)

	dummy_topic = gen_rand(8)
	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, dummy_topic, "bind", "protected")
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)
	
	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Cross-owner binding 
	log("---------------> CROSS OWNER BINDING", 'HEADER') 
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, str(device_keys[dev_name]), follow_id)
	check(r, 200)

	r = bind_unbind(dev_admin_id, dev_admin_key, dev_name, "test", "bind", "protected", from_id =
	app_name)
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)
	
	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Cross-device binding 
	log("---------------> CROSS DEVICE BINDING", 'HEADER') 
	

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, str(device_keys[dev_name]), follow_id)
	check(r, 200)
	

	dummy_dev, dummy_dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = bind_unbind(dummy_dev, dummy_dev_key, dev_name, "test", "bind", "protected", from_id =
	app_name)
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	print("\n\n")
	log("------------------------- UNBIND -------------------------\n\n", 'GREEN')

	#Unbind to unauthorised exchange
	log("---------------> UNBIND FROM UNAUTHORISED EXCHANGE", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "unbind", "protected")
	check(r, 403)
	log("Received 403: OK",'')
		
	#Unbind to non-existent exchange
	log("---------------> UNBIND FROM NON-EXISTENT EXCHANGE", 'HEADER') 

	dummy_exchange = gen_rand(8, prefix= gen_rand(8))

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = bind_unbind(app_name, str(app_keys[app_name]), dummy_exchange, "test", "unbind", "protected")
	check(r, 403)
	log("Received 403: OK",'')

	#Unbind using invalid message_type
	log("---------------> UNBIND USING INVALID MESSAGE-TYPE", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, dev_key, follow_id)
	check(r, 200)

	r = bind_unbind(app_name, app_key, dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')

	r = bind_unbind(app_name, app_key, dev_name, "test", "unbind", gen_rand(8))
	check(r, 400)
	log("Received 400: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)
	
	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Unbind with a different topic from what was requested in follow 
	log("---------------> UNBIND USING UNAUTHORISED TOPIC", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, str(device_keys[dev_name]), follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, gen_rand(8), "unbind", "protected")
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Cross-owner Unbinding 
	log("---------------> CROSS OWNER UNBINDING", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, str(device_keys[dev_name]), follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')

	r = bind_unbind(dev_admin_id, dev_admin_key, dev_name, "test", "unbind", "protected", from_id =
	app_name)
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Cross-device unbinding 
	log("---------------> CROSS DEVICE UNBINDING", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, str(app_keys[app_name]), dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, str(device_keys[dev_name]), follow_id)
	check(r, 200)

	dummy_dev, dummy_dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')

	r = bind_unbind(dummy_dev, dummy_dev_key, dev_name, "test", "unbind", "protected", from_id =
	app_name)
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, str(app_keys[app_name]), dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	print("\n\n")
	log("------------------------- SHARE -------------------------\n\n", 'GREEN')

	#Cross-device share / Share to self
	log("---------------> SHARE TO SELF USING DEVICE APIKEY", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)

	r = share(app_name, app_key, follow_id)
	check(r, 400)
	log("Received 400: OK",'')

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Cross-owner share / Share to self using owner's key
	log("---------------> SHARE TO SELF USING OWNER APIKEY", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)

	r = share(app_admin_id, app_admin_key, follow_id)
	check(r, 400)
	log("Received 400: OK",'')

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Share on behalf of another device
	log("---------------> SHARE BY ANOTHER DEVICE", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)

	dev_copy = copy.deepcopy(device_keys)	
	dev_copy.pop(dev_name, None)

	dummy_dev = random.choice(dev_copy.keys())
	dummy_dev_key = str(dev_copy[dummy_dev])

	r = share(dummy_dev, dummy_dev_key, follow_id)
	check(r, 400)
	log("Received 400: OK",'')

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Share using invalid follow-id
	log("---------------> SHARE USING INVALID FOLLOW-ID", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)

	r = share(dev_name, dev_key, gen_rand(8))
	check(r, 500)
	log("Received 500: OK",'')

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	print("\n\n")
	log("------------------------- FOLLOW -------------------------\n\n", 'GREEN')

	#Invalid from
	log("---------------> FOLLOW USING INVALID FROM-ID", 'HEADER') 

	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_admin_id,app_admin_key, dev_name, "read", from_id = gen_rand(8, prefix = gen_rand(8)))
	check(r,403)
	log("Received 403: OK",'')

	#Invalid to-id
	log("---------------> FOLLOW USING INVALID TO-ID", 'HEADER') 
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")

	r = follow(app_name, str(app_keys[app_name]), gen_rand(8, prefix = gen_rand(8)), "read")
	check(r, 403)
	log("Received 403: OK",'')

	#Invalid validity period - large validity
	log("---------------> FOLLOW USING INVALID VALIDITY PERIOD - LARGE VALIDITY", 'HEADER') 
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	validity = random.randint(1000000, 100000000)
	r = follow(app_name, app_key, dev_name, "read", validity=str(validity))
	check(r, 400)
	log("Received 400: OK",'')
	
	#Invalid validity period - non numeric validity
	log("---------------> FOLLOW USING INVALID VALIDITY PERIOD - NON NUMERIC VALIDITY", 'HEADER') 
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	validity = gen_rand(8) 
	r = follow(app_name, app_key, dev_name, "read", validity=validity)
	check(r, 400)
	log("Received 400: OK",'')

	r = share(dev_name, dev_key, follow_id)
	check(r, 400)
	log("Received 400: OK",'')

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass
	
	#Cross-owner follow
	log("---------------> CROSS-OWNER FOLLOW", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	
	r = follow(dev_admin_id, dev_admin_key, dev_name, "read", from_id = app_name)
	check(r, 403)
	log("Received 403: OK",'')

	#Cross-device follow
	log("---------------> CROSS-DEVICE FOLLOW", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	
	r = follow(dev_name, dev_key, dev_name, "read", from_id = app_name)
	check(r, 202)
	log("Received 202: OK",'')

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Invalid permission
	log("---------------> FOLLOW USING INVALID PERMISSION", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	permission = gen_rand(8)

	r = follow(app_name, app_key, dev_name, permission)
	check(r, 400)
	log("Received 400: OK",'')

	#Invalid message-type 
	log("---------------> FOLLOW USING INVALID MESSAGE-TYPE", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read", message_type=gen_rand(8))
	check(r, 400)
	log("Received 400: OK",'')

	print("\n\n")
	log("------------------------- UNFOLLOW -------------------------\n\n", 'GREEN')

	#Invalid to-id
	log("---------------> UNFOLLOW USING INVALID TO-ID", 'HEADER') 
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, dev_key, follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')
	
	r = unfollow(app_name, app_key, gen_rand(8, prefix = gen_rand(8)), "test",
	"read", "protected")
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, app_key, dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Invalid permission
	log("---------------> UNFOLLOW USING INVALID PERMISSION", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, dev_key, follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 403: OK",'')
	permission = gen_rand(8)

	r = unfollow(app_name, app_key, dev_name, "test", permission, "protected")
	check(r, 400)
	log("Received 400: OK",'')

	r = unfollow(app_name, app_key, dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Cross-owner follow
	log("---------------> CROSS-OWNER UNFOLLOW", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	
	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, dev_key, follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')

	r = unfollow(dev_admin_id, dev_admin_key, dev_name, "test", "read", "protected", from_id = app_name)
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, app_key, dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Cross-device follow
	log("---------------> CROSS-DEVICE UNFOLLOW", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")
	
	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, dev_key, follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')

	r = unfollow(dev_name, dev_key, dev_name, "test", "read", "protected", from_id = app_name)
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, app_key, dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass

	#Invalid message-type 
	log("---------------> UNFOLLOW USING INVALID MESSAGE-TYPE", 'HEADER') 

	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = follow(app_name, app_key, dev_name, "read")
	follow_id = r.json()['follow-id-read']
	check(r, 202)
	
	r = share(dev_name, dev_key, follow_id)
	check(r, 200)

	r = bind_unbind(app_name, str(app_keys[app_name]), dev_name, "test", "bind", "protected")
	check(r, 200)
	log("Received 200: OK",'')

	r = unfollow(app_name, app_key, dev_name, "test","read", message_type=gen_rand(8))
	check(r, 403)
	log("Received 403: OK",'')

	r = unfollow(app_name, app_key, dev_name, "test", "read", "protected")
	check(r, 200)

	cmd = """ docker exec postgres psql -U postgres -c "delete from follow" """

	try:
		p = subprocess.check_output(cmd, shell=True)
	except Exception as e:
		pass
	
	print("\n\n")
	log("------------------------- DEREGISTRATION -------------------------\n\n", 'GREEN')

	#Cross-owner deregistrations
	log("---------------> CROSS-OWNER DEREGISTRATIONS", 'HEADER') 
	
	app_name, app_key = get_entity(device_keys, app_keys, entity_type="app")
	dev_name, dev_key = get_entity(device_keys, app_keys, entity_type="dev")

	r = deregister(dev_admin_id, dev_admin_key, app_name)
	check(r, 403)
	log("Received 403: OK",'')

	r = deregister(app_admin_id, app_admin_key, dev_name)
	check(r, 403)
	log("Received 403: OK",'')

	test_time = time.time() - test_time

	dereg_time = time.time()
	deregistrations(device_keys, app_keys, dev_admin_id, dev_admin_key, app_admin_id,
	app_admin_key)
	dereg_time = time.time() - dereg_time

	time_list = [reg_time, test_time, dereg_time]

	output.put(time_list)


def functional_tests(*args):
	
	if type(args[0]) is list:
	    devices = args[0][0]
	    apps    = args[0][1]

	else:
	    devices = args[0]
	    apps    = args[1]

	dev_admin_id, dev_admin_key = gen_admin()
	app_admin_id, app_admin_key = gen_admin()

	print("\n\n")
	log("========================= FUNCTIONAL TESTS =========================\n\n", 'GREEN', modifier='BOLD')

	reg_time = time.time()
	device_keys, app_keys = registrations(devices, apps, dev_admin_id, dev_admin_key, app_admin_id, app_admin_key)
	reg_time = time.time() - reg_time

	test_time = time.time()
	print("\n\n")
	log("------------------------- SIMPLE READ FOLLOW-SHARE -------------------------\n\n", 'GREEN')
	
	# Follow requests from apps to devices using apps' respective apikeys
	log("---------------> FOLLOW REQUESTS WITH READ PERMISSION ", 'HEADER')
	follow_dev(device_keys, app_keys, as_admin=False, permission="read")

	# Devices read all follow requests and share with apps
	log("---------------> DEVICES READ FOLLOW REQUESTS AND ISSUE SHARE TO APPS", 'HEADER')

	share_dev((apps*devices), dev_admin_id, dev_admin_key)

	# Apps bind to devices' queues
	log("---------------> APPS BIND TO DEVICES", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=devices, as_admin=False, req_type="bind")

	# Devices publish data
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	# Apps unbind from devices
	log("---------------> APPS UNBIND FROM DEVICES", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=devices, as_admin=False, req_type="unbind")

	# Devices again publish messages
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps try to subscribe
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, 0)

	# Apps bind to devices again but this time using admin apikey
	log("---------------> APPS BIND TO DEVICES USING ADMIN APIKEY", 'HEADER')

	bind_unbind_dev(device_keys, app_keys, expected=devices*apps, as_admin=True,
	req_type="bind", admin_id = app_admin_id, admin_key = app_admin_key)

	# Devices publish again
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	# Unbind from devices as admin
	log("---------------> APPS UNBIND FROM DEVICES USING ADMIN APIKEY", 'HEADER')

	bind_unbind_dev(device_keys, app_keys, expected=(devices*apps), as_admin=True,
	req_type="unbind", admin_id = app_admin_id, admin_key = app_admin_key)

	# Devices now publish data
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps try to subscribe but get 0 messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, 0)

	# Apps unfollow all devices
	log("---------------> APPS UNFOLLOW ALL DEVICES USING THEIR RESPECTIVE APIKEYS", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=False, permission="read")

	# Apps try to bind to unfollowed devices
	log("---------------> APPS TRY TO BIND TO UNFOLLOWED DEVICES", 'HEADER')
	bind_unbind_without_follow(device_keys, app_keys, as_admin=False, req_type="bind")


	print("\n\n")
	log("------------------------- FOLLOW REQUESTS AS ADMIN -------------------------\n\n", 'GREEN')

	#Follow requests as admin	
	log("---------------> FOLLOW REQUESTS WITH READ PERMISSION AS ADMIN", 'HEADER')
	follow_dev(device_keys, app_keys, as_admin=True, permission="read", admin_id = app_admin_id, admin_key = app_admin_key)

	#Devices share with apps
	log("---------------> DEVICES READ FOLLOW REQUESTS AND ISSUE SHARE TO APPS", 'HEADER')

	share_dev((apps*devices), admin_id = dev_admin_id, admin_key = dev_admin_key)

	# Apps bind to devices' queues
	log("---------------> APPS BIND TO DEVICES", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=devices, as_admin=False, req_type="bind")

	# Devices publish data
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	# Apps unfollow all devices
	log("---------------> APPS UNFOLLOW ALL DEVICES USING THEIR ADMIN APIKEYS", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=True, permission="read", admin_id = app_admin_id, admin_key = app_admin_key)

	# Apps try to bind to unfollowed devices
	log("---------------> APPS TRY TO BIND TO UNFOLLOWED DEVICES", 'HEADER')
	bind_unbind_without_follow(device_keys, app_keys, as_admin=False, req_type="bind")


	print("\n\n")
	log("------------------------- FOLLOW REQUESTS WITH WRITE PERMISSION -------------------------\n\n", 'GREEN')

	#Follow requests for write	
	log("---------------> FOLLOW REQUESTS WITH WRITE PERMISSIONS", 'HEADER')
	follow_dev(device_keys, app_keys, as_admin=False, permission="write")

	#Devices share with apps with write access
	log("---------------> DEVICES READ FOLLOW REQUESTS AND ISSUE SHARE TO APPS", 'HEADER')
	share_dev((apps*devices), dev_admin_id, dev_admin_key)

	#Apps publish to command queue of devices
	log("---------------> APPS PUBLISH TO COMMAND EXCHANGE OF DEVICES", 'HEADER')
	app_publish(device_keys, app_keys, 202)

	#Devices subscribe to their command queue
	log("---------------> DEVICES SUBSCRIBE TO THEIR COMMAND QUEUES", 'HEADER')
	dev_subscribe(apps, device_keys, apps)

	#Follow requests for write	
	log("---------------> APPS WITH WRITE ACCESS UNFOLLOW DEVICES", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=False, permission="write")

	#Apps publish to command queue of devices
	log("---------------> APPS TRY TO PUBLISH TO COMMAND EXCHANGE OF UNFOLLOWED DEVICES", 'HEADER')
	app_publish(device_keys, app_keys, 202)


	print("\n\n")
	log("------------------------- FOLLOW REQUESTS WITH READ-WRITE PERMISSIONS -------------------------\n\n", 'GREEN')

	#Apps request follow with read-write permissions
	log("---------------> APPS REQUEST FOLLOW WITH READ-WRITE PERMISSIONS", 'HEADER')
	follow_dev(device_keys, app_keys, as_admin=False, permission="read-write")

	#Devices approve issue share to apps
	log("---------------> DEVICES APPROVE READ-WRITE FOLLOW REQUESTS WITH SHARE", 'HEADER')
	share_dev((devices*apps*2), dev_admin_id, dev_admin_key)

	#Apps publish to command queue of devices
	log("---------------> APPS PUBLISH TO COMMAND EXCHANGE OF DEVICES", 'HEADER')
	app_publish(device_keys, app_keys, 202)

	#Devices subscribe to their command queue
	log("---------------> DEVICES SUBSCRIBE TO THEIR COMMAND QUEUES", 'HEADER')
	dev_subscribe(apps, device_keys, apps)
	
	# Apps bind to devices' queues
	log("---------------> APPS BIND TO DEVICES", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=(2*devices), as_admin=False, req_type="bind")

	# Devices publish again
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	#Apps relinquish write permission
	log("---------------> APPS WITH WRITE ACCESS UNFOLLOW DEVICES", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=False, permission="write")

	#Apps publish to command queue of devices
	log("---------------> APPS TRY TO PUBLISH TO COMMAND EXCHANGE OF UNFOLLOWED DEVICES", 'HEADER')
	app_publish(device_keys, app_keys, 202)

	# Devices publish again
	log("---------------> DEVICES PUBLISH DATA AFTER WRITE UNFOLLOW", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA AFTER WRITE UNFOLLOW", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	# Apps unfollow with read permissions
	log("---------------> APPS UNFOLLOW DEVICES WITH READ ACCESS", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=True, permission="read", admin_id = app_admin_id, admin_key = app_admin_key)

	# Apps try to bind to unfollowed devices
	log("---------------> APPS TRY TO BIND TO UNFOLLOWED DEVICES", 'HEADER')
	bind_unbind_without_follow(device_keys, app_keys, as_admin=False, req_type="bind")

	print("\n\n")
	log("------------------------- BIND USING ADMIN APIKEY -------------------------\n\n", 'GREEN')

	#Apps obtain read-write follow
	log("---------------> APPS FOLLOW WITH READ-WRITE PERMISSIONS", 'HEADER')
	follow_dev(device_keys, app_keys, as_admin=False, permission="read-write")

	#Devices approve issue share to apps
	log("---------------> DEVICES APPROVE READ-WRITE FOLLOW REQUESTS WITH SHARE", 'HEADER')
	share_dev((devices*apps*2), dev_admin_id, dev_admin_key)

	# Apps bind to devices' queues
	log("---------------> APPS BIND TO DEVICES WITH ADMIN APIKEY", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=(2*devices*apps), as_admin=True, req_type="bind", admin_id = app_admin_id, admin_key = app_admin_key)

	# Devices publish again
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	# Apps unfollow with read permissions
	log("---------------> APPS UNFOLLOW DEVICES WITH READ-WRITE ACCESS", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=True, permission="read-write", admin_id = app_admin_id, admin_key = app_admin_key)

	# ===============================Diagnostics channel ===============================

	# Follow requests from apps to devices using apps' respective apikeys for diagnostics
	# channel

	print("\n\n")
	log("------------------------- DIAGNOSTICS CHANNEL TESTS -------------------------\n\n", 'GREEN')

	log("---------------> FOLLOW REQUESTS WITH READ PERMISSION TO DIAGNOSTICS CHANNEL", 'HEADER')
	follow_dev(device_keys, app_keys, as_admin=False, permission="read",
	message_type="diagnostics")

	# Devices read all follow requests and share with apps
	log("---------------> DEVICES READ FOLLOW REQUESTS AND ISSUE SHARE TO APPS", 'HEADER')

	share_dev((apps*devices), dev_admin_id, dev_admin_key)

	# Apps bind to devices' diagnostics exchanges
	log("---------------> APPS BIND TO DEVICES' DIAGNOSTICS CHANNEL", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=devices, as_admin=False, req_type="bind", message_type="diagnostics")

	# Devices publish data to diagnostics exchanges
	log("---------------> DEVICES PUBLISH DATA TO DIAGNOSTICS CHANNEL", 'HEADER')
	dev_publish(device_keys, message_type="diagnostics")

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	# Apps unbind from devices diagnostics channel
	log("---------------> APPS UNBIND FROM DEVICES' DIAGNOSTICS CHANNEL", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=devices, as_admin=False, req_type="unbind", message_type="diagnostics")

	# Devices again publish messages to diagnostics channel
	log("---------------> DEVICES PUBLISH DATA TO DIAGNOSTICS CHANNEL", 'HEADER')
	dev_publish(device_keys, message_type="diagnostics")

	# Apps try to subscribe
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, 0)

	# Apps bind to devices using admin apikey
	log("---------------> APPS BIND TO DEVICES USING ADMIN APIKEY", 'HEADER')

	bind_unbind_dev(device_keys, app_keys, expected=devices*apps, as_admin=True, req_type="bind", message_type="diagnostics", admin_id = app_admin_id, admin_key = app_admin_key)

	# Devices publish again to diagnostics channel
	log("---------------> DEVICES PUBLISH DATA TO DIAGNOSTICS CHANNEL", 'HEADER')
	dev_publish(device_keys, message_type="diagnostics")

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices)

	# Unbind from devices as admin
	log("---------------> APPS UNBIND FROM DEVICES USING ADMIN APIKEY", 'HEADER')

	bind_unbind_dev(device_keys, app_keys, expected=(devices*apps), as_admin=True, req_type="unbind", message_type="diagnostics", admin_id = app_admin_id, admin_key = app_admin_key)

	# Devices now publish data to diagnostics channel
	log("---------------> DEVICES PUBLISH DATA TO DIAGNOSTICS CHANNEL", 'HEADER')
	dev_publish(device_keys, message_type="diagnostics")

	# Apps try to subscribe but get 0 messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, 0)

	# Apps unfollow all devices
	log("---------------> APPS UNFOLLOW ALL DEVICES USING THEIR RESPECTIVE APIKEYS", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=False, permission="read", message_type="diagnostics")

	# Apps try to bind to unfollowed devices' diagnostics channel
	log("---------------> APPS TRY TO BIND TO UNFOLLOWED DEVICES' DIAGNOSTICS CHANNEL", 'HEADER')
	bind_unbind_without_follow(device_keys, app_keys, as_admin=False, req_type="bind", message_type="diagnostics")

	# ===============================Priority queue ===============================

	print("\n\n")
	log("------------------------- PRIORITY QUEUE TESTS -------------------------\n\n", 'GREEN')

	# Follow requests from apps to devices using apps' respective apikeys
	log("---------------> FOLLOW REQUESTS WITH READ PERMISSION", 'HEADER')
	follow_dev(device_keys, app_keys, as_admin=False, permission="read",)

	# Devices read all follow requests and share with apps
	log("---------------> DEVICES READ FOLLOW REQUESTS AND ISSUE SHARE TO APPS", 'HEADER')

	share_dev((apps*devices), dev_admin_id, dev_admin_key)

	# Apps bind to devices' diagnostics exchanges
	log("---------------> APPS BIND TO DEVICES PROTECTED CHANNEL", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=devices, as_admin=False, req_type="bind",
	is_priority = "true")

	# Devices publish data to diagnostics exchanges
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices, message_type = "priority")

	# Apps unbind from devices diagnostics channel
	log("---------------> APPS UNBIND FROM DEVICES", 'HEADER')
	bind_unbind_dev(device_keys, app_keys, expected=devices, as_admin=False, req_type="unbind",
	is_priority = "true")

	# Devices again publish messages to diagnostics channel
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps try to subscribe
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, 0, message_type = "priority")

	# Apps bind to devices using admin apikey
	log("---------------> APPS BIND TO DEVICES USING ADMIN APIKEY", 'HEADER')

	bind_unbind_dev(device_keys, app_keys, expected=devices*apps, as_admin=True,
	req_type="bind", is_priority = "true", admin_id = app_admin_id, admin_key = app_admin_key)

	# Devices publish again to diagnostics channel
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps subscribe to messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, devices, message_type = "priority")

	# Unbind from devices as admin
	log("---------------> APPS UNBIND FROM DEVICES USING ADMIN APIKEY", 'HEADER')

	bind_unbind_dev(device_keys, app_keys, expected=(devices*apps), as_admin=True,
	req_type="unbind", is_priority = "true", admin_id = app_admin_id, admin_key = app_admin_key)

	# Devices now publish data to diagnostics channel
	log("---------------> DEVICES PUBLISH DATA", 'HEADER')
	dev_publish(device_keys)

	# Apps try to subscribe but get 0 messages
	log("---------------> APPS TRY TO READ PUBLISHED DATA", 'HEADER')
	app_subscribe(devices, app_keys, 0, message_type = "priority")

	# Apps unfollow all devices
	log("---------------> APPS UNFOLLOW ALL DEVICES USING THEIR RESPECTIVE APIKEYS", 'HEADER')
	unfollow_dev(device_keys, app_keys, as_admin=False, permission="read")

	# Apps try to bind to unfollowed devices' diagnostics channel
	log("---------------> APPS TRY TO BIND TO UNFOLLOWED DEVICES' DIAGNOSTICS CHANNEL", 'HEADER')
	bind_unbind_without_follow(device_keys, app_keys, as_admin=False, req_type="bind",
	is_priority = "true")

	test_time = time.time() - test_time


	dereg_time = time.time()
	deregistrations(device_keys, app_keys, dev_admin_id, dev_admin_key, app_admin_id,
	app_admin_key)
	dereg_time = time.time() - dereg_time

	time_list = [reg_time, test_time, dereg_time]

	output.put(time_list)

def concurrency_tests():

    concurrent_processes = random.randint(2, 7)

    num_list = []

    for num in range(concurrent_processes):

	devices = random.randint(2,7)
	apps	= random.randint(2,7)
	
	num_list.append([devices,apps])

    processes = [mp.Process(target=functional_tests, args=(num,)) for num in num_list]
    
    for p in processes:
	p.start()

    for p in processes:
	p.join()

    i = 1

    print("\n\n")
    log("=========================All tests have passed=========================", 'GREEN', modifier='BOLD')
    
    for p in processes:

	time_list = output.get()

	print("\n\n")
	log("------------------------- Process "+ str(i) +" -------------------------\n\n", 'GREEN')
	log("Time taken for registrations    :	    "+str(time_list[0])+"s",'GREEN')
	log("Time taken for test cases       :	    "+str(time_list[1])+"s",'GREEN')
	log("Time taken for deregistrations  :	    "+str(time_list[2])+"s",'GREEN')

	i = i + 1

    sys.exit(0)

def start_tests(devices, apps, args):
	
	if args.choice == "fxnl":
		
		functional_tests(devices, apps)
		time_list = output.get()

	elif args.choice == "sec":
		
		security_tests()
		time_list = output.get()

	elif args.choice == "concr":
		
		concurrency_tests()

	print("\n\n")
	log("=========================All tests have passed=========================", 'GREEN', modifier='BOLD')
	log("Time taken for registrations    :	    "+str(time_list[0])+"s",'GREEN')
	log("Time taken for test cases       :	    "+str(time_list[1])+"s",'GREEN')
	log("Time taken for deregistrations  :	    "+str(time_list[2])+"s",'GREEN')

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Test cases for Corinthian')
	subparser = parser.add_subparsers(dest="choice")

	func_parser = subparser.add_parser("fxnl", help="Performs functional tests")

	func_parser.add_argument('-d', '--devices', action="store", dest="devices", type=int, help="No. of devices to run the tests")
	func_parser.add_argument('-a', '--apps', action="store", dest="apps", type=int, help="No. of apps to run the tests")
	func_parser.add_argument('--random', action="store_true", help="Run tests with random devices and apps")

	sec_parser = subparser.add_parser("sec", help="Performs security tests")

	conc_parser = subparser.add_parser("concr", help="Performs concurrency tests")

	conc_parser.add_argument('-d', '--devices', action="store", dest="devices", type=int, help="No. of devices to run the tests")
	conc_parser.add_argument('-a', '--apps', action="store", dest="apps", type=int, help="No. of apps to run the tests")
	conc_parser.add_argument('--random', action="store_true", help="Run tests with random devices and apps")
	
	all_parser = subparser.add_parser("all", help="Performs all of the above tests")

	all_parser.add_argument('-d', '--devices', action="store", dest="devices", type=int, help="No. of devices to run the tests")
	all_parser.add_argument('-a', '--apps', action="store", dest="apps", type=int, help="No. of apps to run the tests")
	all_parser.add_argument('--random', action="store_true", help="Run tests with random devices and apps")
	
	args = parser.parse_args()

	devices = 0
	apps 	= 0					

	if args.choice <> "sec":

		if args.random:
			devices = random.randint(10,20)
			apps 	= random.randint(10,20)
		else:
			devices = args.devices
			apps = args.apps
		
	logging.basicConfig(format='%(asctime)s %(levelname)-6s %(message)s', level=logging.DEBUG,
						datefmt='%Y-%m-%d %H:%M:%S')
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)

	start_tests(devices, apps, args)
