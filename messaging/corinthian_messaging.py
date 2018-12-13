#!python3
# Common routines for communicating with the Corinthian middleware.
# Author: Poorna Chandra Tejasvi

from __future__ import print_function
import json
import urllib3
import requests # for https requests
import logging
from requests.adapters import HTTPAdapter
logger = logging.getLogger(__name__)
import os.path

#=========================================
# Middleware settings (constants):
#=========================================

# IP address of the middleware 
Corinthian_ip_address = "localhost"

# url for sending http requests to the apigateway 
Corinthian_base_url = "https://"+Corinthian_ip_address

# port number for publish/get using AMQP
Corinthian_port = 5671

# Admin apikey 
# (read from a file named "admin.passwd" in the same folder as this script)
admin_passwd_file_location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
admin_passwd_file =  os.path.join(admin_passwd_file_location, "admin.passwd")
admin_apikey = open(admin_passwd_file,"r").read()[:-1]

# disable SSL check warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a requests session
def create_session():
	s = requests.Session();
	s.mount(Corinthian_base_url, HTTPAdapter(pool_connections=1))
	return s

# Common status code check for all APIs
def check(response, code):
	assert(response.status_code == code), "URL = "+response.url+"\n"+"Status code = " \
	+str(response.status_code)+"\n"+"Message = "+response.text

def register(entity_id):
	url = Corinthian_base_url + "/owner/register-entity"
	headers = {"id": "admin", "apikey": admin_apikey, "entity": entity_id, "is-autonomous": "true"}
	r = requests.post(url=url, headers=headers, data="{\"test\":\"schema\"}", verify=False)
	check(r,201)
	return r.json()["apikey"]

def deregister(entity_id):

	url = Corinthian_base_url + "/owner/deregister-entity"
	headers = {"id": "admin", "apikey": admin_apikey, "entity": entity_id}
	r = requests.post(url=url, headers=headers, verify=False)
	check(r,200)
	return True

def block_unblock(ID, apikey, entity_id, req_type):

	url = Corinthian_base_url 
	if req_type == "block":
		url = url + "/owner/block"
	elif req_type == "unblock":
		url = url + "/owner/unblock"
	headers = {"id": ID, "apikey": apikey, "entity": entity_id}
	r = requests.post(url=url, headers=headers, verify=False)
	check(r,200)

def permissions(ID, apikey, entity_id=""):

	url = Corinthian_base_url + "/entity/permissions"
	headers = {}
	if entity_id:
		headers['entity'] = entity_id
	headers ['id'] = ID
	headers ['apikey'] = apikey
	r = requests.get(url=url, headers=headers, verify=False)
	check(r,200)

def publish(ID, apikey, to, topic, message_type, data, session=None):

	url = Corinthian_base_url + "/entity/publish"
	headers = {"id": ID, "apikey": apikey, "to": to, "subject": topic, "message-type": message_type, "content-type": "text/plain"}
	if(session):
		r = session.post(url=url,headers=headers,data=data,verify=False)
	else:
		r = requests.post(url=url,headers=headers,data=data,verify=False)
	check(r,202)
	return True

def follow(ID, apikey, to_id, permission, from_id="", topic ="", validity = "", message_type=""):

	url = Corinthian_base_url + "/entity/follow"
	headers = {}
	if from_id:
		headers['from'] = from_id
	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to_id
	if topic:
		headers['topic'] = topic
	else:
		headers['topic'] = "#"
	if validity:
		headers['validity'] = validity
	else:
		headers['validity'] = "24"
	
	if message_type:
		headers['message-type'] = message_type
	headers['permission'] = permission
	
	r = requests.post(url=url,headers=headers,verify=False)
	check(r,202)
	return r

def reject_follow(ID, apikey, follow_id):

	url = Corinthian_base_url + "/entity/reject-follow"
	headers = {"id": ID, "apikey": apikey, "follow-id": follow_id}
	r = requests.post(url=url, headers=headers, verify=False)
	check(r,200)

def unfollow(ID, apikey, to, topic, permission, message_type, from_id=""):

	url = Corinthian_base_url + "/entity/unfollow"
	headers = {}
	if from_id:
		headers['from'] = from_id
	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to
	headers['topic'] = "#"
	headers['permission'] = permission
	headers['message-type'] = message_type 
	
	r = requests.post(url=url,headers=headers,verify=False)
	check(r,200)

def share(ID, apikey, follow_id):

	url = Corinthian_base_url + "/entity/share"
	headers = {"id": ID, "apikey": apikey, "follow-id": follow_id}
	r = requests.post(url=url, headers=headers, verify=False)
	check(r,200)

def bind_unbind(ID, apikey, to, topic, message_type, from_id="", is_priority="false", req_type="bind"):

	url = Corinthian_base_url
	headers = {}

	if req_type == "bind":
		url = url + "/entity/bind"
	elif req_type == "unbind":
		url = url + "/entity/unbind"

	if from_id:
		headers['from'] = from_id

	headers['message-type'] = message_type
	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to
	headers['topic'] = topic
	headers['is-priority'] = is_priority 
	r = requests.post(url=url, headers=headers, verify=False)
	check(r,200)

def subscribe(ID, apikey, message_type="", num_messages="",session=None):

	url = Corinthian_base_url + "/entity/subscribe"
	headers = {}
	if message_type:
		headers['message-type'] = message_type
	if num_messages:
		headers['num-messages'] = num_messages
	headers['id'] = ID
	headers['apikey'] = apikey
	if(session):
		r = session.get(url=url, headers=headers, verify=False)
	else:
		r = requests.get(url=url, headers=headers, verify=False)
	check(r,200)
	return r

def follow_requests(ID, apikey, request_type):

	url = Corinthian_base_url
	if request_type == "requests":
		url = url + "/entity/follow-requests"
	elif request_type == "status":
		url = url + "/entity/follow-status"
	headers = {"id": ID, "apikey": apikey}
	r = requests.get(url=url, headers=headers, verify=False)
	check(r,200)
	return r


#=================================================
# Testbench
#=================================================
import time
   
def run_test():
	try:
		# Register device1
		device1_apikey = register("device1")
		print("REGISTER: Registering device1 successful. apikey = {}".format(device1_apikey))
		
		# Register application1
		application1_apikey = register("application1")
		print("REGISTER: Registering application1 successful. apikey = {}".format(application1_apikey))
		
		# Let application1 follow device1 (read)
		follow_response = follow("admin/application1", application1_apikey,"admin/device1","read")
		print("FOLLOW: application1 sent a request to follow(read) device1")
		
		# Let application1 follow device1 (write)
		follow_response = follow("admin/application1", application1_apikey,"admin/device1","write")
		print("FOLLOW: application1 sent a request to follow(write) device1")
		
		# Get device1 to check all follow requests forwarded to it
		# and approve each request
		check_follow_response = follow_requests("admin/device1", device1_apikey, "requests")
		requests = check_follow_response.json()
		for r in requests:
			requesting_entity = r["from"]
			permission_sought = r["permission"]
			follow_id = r["follow-id"]
			print ("FOLLOW: device1 received a follow request from",requesting_entity,"for permission=",permission_sought)
			share_status = share("admin/device1", device1_apikey, follow_id)
			print ("SHARE: device1 sent a share request for entity",requesting_entity,"for permission=",permission_sought)
		# Get application1 to check for notifications (responses to its follow request)
		follow_status_response = follow_requests("admin/application1", application1_apikey, "status")
		statuses = follow_status_response.json()
		for status in statuses:
			assert(status["status"] == "approved")
		print ("FOLLOW: application1's follow request was Approved.")
		# Get application1 to bind to device1's protected stream
		success = bind_unbind("admin/application1", application1_apikey, "admin/device1","#","protected")
		print ("BIND: application1 sent a bind request for device1.protected.")
		# Try publish/subscribe using HTTP
		print ("----------------------------------------")
		print (" Performing publish/get using HTTP ")
		print ("----------------------------------------")
		
		# Get device1 to publish some stuff.
		for i in range (10):
			data = {}
			data['value']=str(100+i)
			data['using']="http"
			print("PUBLISH: Publishing from device1. Data=",data)
			success = publish("admin/device1",device1_apikey, "admin/device1", "#", "protected", json.dumps(data))
			
		# Get application1 to print the data it has susbscribed to
		messages = subscribe("admin/application1", application1_apikey)
		print ("SUBSCRIBE: application1 received the following data from device1:")
		
		for m in messages.json():
			print(m)
	except:
		print ("An exception occured.")
		raise
	finally:        
		print("")
		# De-register device1
		print("DE-REGISTER: De-registering device1: ",end=''),
		success = deregister("admin/device1")
		if(success):
			print("success")
		
		# De-register application1
		print("DE-REGISTER: De-registering application1: ",end=''),
		success = deregister("admin/application1")
		if(success):
			print("success")

if __name__=='__main__':
	# set logging level to DEBUG
	logging.basicConfig(level=logging.DEBUG)
	# suppress debug messages from other modules used.
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("pika").setLevel(logging.WARNING)
	run_test()
