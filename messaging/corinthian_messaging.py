#!python3
# 
# Common routines for communicating with the 
# Corinthian middleware using HTTP and AMQP protocols.
# The HTTP messaging uses Python's Requests library whereas
# the AMQP messaging uses Python's Pika library.
# 
# NOTE: Publish/Get can be performed using both HTTPS/AMQP.
# However, registration/follow/share/bind etc is implemented only for HTTPS. 
# 
# Author: Neha Karanjkar


from __future__ import print_function
import json
import urllib3
import requests # for https requests
import pika     # for amqp requests
import logging
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

#=========================================
# Middleware settings (constants):
#=========================================

# IP address of the middleware 
Corinthian_ip_address = "localhost"


# url for sending http requests to the apigateway 
Corinthian_base_url = "https://"+Corinthian_ip_address

# port number for publish/get using AMQP
Corinthian_port = 5672

#Admin apikey 
admin_apikey = open("admin.passwd","r").read()[:-1]

# disable SSL check warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#Initialise sessions
s = requests.Session();
s.mount(Corinthian_base_url, HTTPAdapter(pool_connections=10))


#Common status code check for all APIs
#=====================================

def check(response, code):
    assert(response.status_code == code), "URL = "+response.url+"\n"+"Status code = " \
    +str(response.status_code)+"\n"+"Message = "+response.text

#=========================================
# Routines  using https communications:

def register(entity_id):
	
	url = Corinthian_base_url + "/register"
	headers = {"id": "admin", "apikey": admin_apikey, "entity": entity_id, "is-autonomous": "true"}
	r = s.post(url=url, headers=headers, data="{\"test\":\"schema\"}", verify=False)
	check(r,201)

	return r.json()["apikey"]

def deregister(entity_id):

	url = Corinthian_base_url + "/deregister"
	headers = {"id": "admin", "apikey": admin_apikey, "entity": entity_id}
	r = s.get(url=url, headers=headers, verify=False)
	check(r,200)

def block_unblock(ID, apikey, entity_id, req_type):
	
	url = Corinthian_base_url 
	
	if req_type == "block":
		url = url + "/block"
	elif req_type == "unblock":
		url = url + "/unblock"

	headers = {"id": ID, "apikey": apikey, "entity": entity_id}
	r = s.get(url=url, headers=headers, verify=False)

	check(r,200)

def permissions(ID, apikey, entity_id=""):

	url = Corinthian_base_url + "/permissions"

	headers = {}

	if entity_id:
		headers['entity'] = entity_id

	headers ['id'] 		= ID
	headers	['apikey'] 	= apikey

	r = s.get(url=url, headers=headers, verify=False)
	check(r,200)

def publish(ID, apikey, to, topic, message_type, data):

	url = Corinthian_base_url + "/publish"
	headers = {"id": ID, "apikey": apikey, "to": to, "subject": topic, "message-type": message_type, "content-type": "text/plain"}
	r = s.post(url=url,headers=headers,data=data,verify=False)
	check(r,202)

def follow(ID, apikey, to_id, permission, from_id="", topic ="", validity = "", message_type=""):

	url = Corinthian_base_url + "/follow"
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
	
	r = s.get(url=url,headers=headers,verify=False)
	check(r,202)

	return r

def reject_follow(ID, apikey, follow_id):
	
	url =	Corinthian_base_url + "/reject-follow"
	headers = {"id": ID, "apikey": apikey, "follow-id": follow_id}
	r = s.get(url=url, headers=headers, verify=False)
	check(r,200)
	
def unfollow(ID, apikey, to, topic, permission, message_type, from_id=""):

	url = Corinthian_base_url + "/unfollow"
	headers = {}

	if from_id:
		headers['from'] = from_id

	headers['id'] = ID
	headers['apikey'] = apikey
	headers['to'] = to
	headers['topic'] = "#"
	headers['permission'] = permission
	headers['message-type'] = message_type 
	
	r = s.get(url=url,headers=headers,verify=False)
	check(r,200)

def share(ID, apikey, follow_id):

	url = Corinthian_base_url + "/share"
	headers = {"id": ID, "apikey": apikey, "follow-id": follow_id}
	r = s.get(url=url, headers=headers, verify=False)
	check(r,200)

def bind_unbind(ID, apikey, to, topic, message_type, from_id="", is_priority="false", req_type="bind"):

	url = Corinthian_base_url
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
	check(r,200)

def subscribe(ID, apikey, message_type="", num_messages=""):

	url = Corinthian_base_url + "/subscribe"
	headers = {}

	if message_type:
		headers['message-type'] = message_type

	if num_messages:
		headers['num-messages'] = num_messages

	headers['id'] = ID
	headers['apikey'] = apikey

	r = s.get(url=url, headers=headers, verify=False)
	check(r,200)

	return r

def follow_requests(ID, apikey, request_type):

	url = Corinthian_base_url

	if request_type == "requests":
		url = url + "/follow-requests"
	elif request_type == "status":
		url = url + "/follow-status"

	headers = {"id": ID, "apikey": apikey}

	r = s.get(url=url, headers=headers, verify=False)
	check(r,200)
	
	return r

#==========================================
# publish/get using AMQP
#==========================================

class PublishChannel(object):
    def __init__(self, entity_id, apikey, exchange):
        """
        Open a channel for publishing.
        Arguments:
            entity_id: name of entity. Eg "dev0"
            apikey  : apikey of the entity
            exchange: default exchange to publish to. Eg: "dev0.protected" or "dev0.configure"
        """
        self.entity_id = entity_id
        self.apikey =apikey
        self.exchange=str(exchange)
        
        # open a channel
        credentials = pika.PlainCredentials(entity_id, apikey)
        parameters = pika.ConnectionParameters(Corinthian_ip_address, Corinthian_port, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        self.channel = connection.channel()

    def publish(self, data, exchange=None, routing_key=None):
        """
        Blocking routine to 
        publish data to an already open channel.
        Returns True if publish succeeded.
        Arguments:
            data: data to be published. Should be a valid json string.
            exchange (optional) : name of the exchange. If not specified, the default value set during init is used.
            routing_key: optional
        Returns:
            True if success else returns False
        """
        if routing_key == None:
            routing_key = '<unspecified>'
        if exchange == None:
            exchange = self.exchange
        success = self.channel.basic_publish(exchange=exchange, routing_key=routing_key, body=str(data))
        if(not success):
            logger.error("publish (amqp) failed for exchange {}".format(exchange))
        return success
    def close(self):
        self.channel.close()


class SubscribeChannel(object):
    def __init__(self, entity_id, apikey, queue):
        """
        Open a channel for getting messages.
        Arguments:
            entity_id: name of entity or exchange. Eg "app0"
            apikey   : apikey of the entity
            queue    : default queue  from which to fetch messages. Eg: "app0" or "dev0.notify" 
        """
        self.entity_id = entity_id
        self.apikey =apikey
        self.queue=str(queue)
        # open a channel
        credentials = pika.PlainCredentials(entity_id, apikey)
        parameters = pika.ConnectionParameters(IDEAM_ip_address, IDEAM_port, '/', credentials)
        connection = pika.BlockingConnection(parameters)
        self.channel = connection.channel()

    def get(self, max_entries, queue=None):
        """
        Get accumulated messages using the 
        blocking basic_get() function.
        Limit the number of entries fetched to <max_entries>.
        Arguments:
            queue (optional) : if specified fetch entries from this queue.
            else fetch from the default queue. Examples: "app0" or "dev1.configure"
        Returns:
            True, a list of messages if success, else returns False, None
        """
        if(queue == None):
            queue=self.queue
        
        assert(isinstance(max_entries, int))
        data=[]
        for i in range(max_entries):
            method, properties, body = self.channel.basic_get(queue)
            if method:
                # convert the message from byte format to a python dict
                m = json.loads(body.decode('utf-8'))
                data.append(m)
                # send an 'ack'
                self.channel.basic_ack(method.delivery_tag)
            else:
                # there seem to be no more messages.
                break
        return True, data
    def close(self):
        self.channel.close()

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
	    follow_id	      = r["follow-id"]
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
        
        #=========================================
        # Try publish/subscribe using HTTP
        #=========================================
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
        
#        #=========================================
#        # Try publish/subscribe using AMQP
#        #=========================================
#        print ("----------------------------------------")
#        print (" Performing publish/get using AMQP ")
#        print ("----------------------------------------")
#        # Get device1 to publish some stuff.
#        device1_channel =  PublishChannel("admin/device1",device1_apikey, "admin/device1.protected")
#        for i in range (10):
#            data = {}
#            data['value']=str(100+i)
#            data['using']="amqp"
#            print("PUBLISH: Publishing from device1. Data=",data)
#            success = device1_channel.publish(json.dumps(data))
#            assert(success)
#        device1_channel.close()
#        
#        # Get application1 to print the data it has susbscribed to
#        application1_channel = SubscribeChannel("admin/application1",application1_apikey,"admin/application1")
#        success, messages = application1_channel.get(max_entries=100)
#        assert(success)
#        print ("SUBSCRIBE: application1 received the following data from device1:")
#        for m in messages:
#            print(m)
#        application1_channel.close()
#        #=========================================
    except:
        print ("An exception occured.")
        raise
    finally:        
        print("")
        # De-register device1
        print("DE-REGISTER: De-registering device1: ",end=''),
        success = deregister("admin/device1")
        print("success = ",success)
        
        # De-register application1
        print("DE-REGISTER: De-registering application1: ",end=''),
        success = deregister("admin/application1")

if __name__=='__main__':
    
    # set logging level to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)
    
    run_test()
