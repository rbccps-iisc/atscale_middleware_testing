#!python3
#
# Common routines for communicating with the 
# IDEAM middleware using python's requests library.
#
# Author: Neha Karanjkar


from __future__ import print_function
import requests
import json
import urllib3
import logging
logger = logging.getLogger(__name__)


#----------------------------------------
# Middleware settings:
#----------------------------------------

# IP address of the middleware server
IDEAM_ip_address = "127.0.0.1"

# api version
IDEAM_api = "1.0.0"

# urls for sending https requests to the apigateway 
IDEAM_base_url = "https://"+IDEAM_ip_address+":8443/api/"+IDEAM_api

# disable SSL check warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 

# sample schema for registering a streetlight device.
import streetlight_schema
#----------------------------------------



def register(self_id):
    """ Register an entity with the given self_id.
    If registration succeeds return True, <apikey>
    else return False, 0
    """
    register_url = IDEAM_base_url+ "/register"
    register_headers = {'apikey': 'guest', 'content-type':'application/json'}
    response = requests.post(url=register_url, headers=register_headers, data=streetlight_schema.get_data_from_schema(self_id), verify=False)
    r = response.json()
    s = response.status_code
    if( s == 200 and r["Registration"] == "success"):
        return True, r["apiKey"]
    else:
        logger.error("registration failed for entity {} with response {}".format(self_id,response.text))
        return False, 0


def deregister(self_id):
    """ De-register an entity with the given self_id.
    If de-registration succeeds return True else return False.
    """
    deregister_url = IDEAM_base_url+ "/register"
    deregister_headers = {'apikey': 'guest'}
    d = {"id":str(self_id)}
    response = requests.delete(url=deregister_url, headers=deregister_headers, data = json.dumps(d), verify=False)
    r = response.json()
    s = response.status_code
    if( s == 200 and r["De-Registration"] == "success"):
        return True
    else:
        logger.error("de-registration failed for entity {} with response {}".format(self_id,response.text))
        return False

# Publish
def publish(entity_id, stream, apikey, data):
    """ Publish data to a specified entity's exchange.

    Arguments:
        entity_id : name of the entity/exchange
        stream    : can be public/protected/configure etc.
        apikey    : apikey of the publisher
        data      : data (json string) to be published.
    """
    
    publish_url = IDEAM_base_url +"/publish/"+entity_id+"."+stream
    publish_headers = {"apikey":str(apikey)}
    response = requests.post(url=publish_url, headers=publish_headers, data=data, verify=False)
    s = response.status_code
    if( s == 202):
        return True
    else:
        logger.error("publish (stream={}) failed for entity {} with status code {} and response {}".format(stream,entity_id,s,response.text))
        return False, 0


# Follow 
def follow(self_id, apikey, entity_id, permission):
    """ Send a follow request to a specified entity.

    Arguments:
        self_id   : the id of the entity sending the follow request
        apikey    : apikey of the entity sending the follow request
        entity_id : id of the target entity which we wish to follow
        permission: can be "read" or "write" or "readwrite"
    """

    follow_url = IDEAM_base_url +"/follow"
    follow_headers = {"Content-Type": "application/json", "apikey":str(apikey)}
    data = {"entityID": str(entity_id), "permission":permission, "validity": "10D", "requestorID":str(self_id)}
    response = requests.post(url=follow_url, headers=follow_headers, data=json.dumps(data), verify=False)
    s = response.status_code
    if( s == 200):
        return True
    else:
        logger.error("follow request failed for sender entity {} with status code {} and response {}".format(self_id,s,response.text))
        return False, 0


# Subscribe 
def subscribe(self_id, stream, apikey, max_entries):
    """ Fetch data from the middleware meant for this entity
    
    Arguments:
        self_id  : the id of the entity from which to fetch data 
        stream   : stream from which to fetch data. (None/protected/public/configure...)
        apikey   : apikey of the entity sending the subscribe request
        max_entries : max number of entries to fetch at a time
    """
    if stream!=None:
        self_id = str(self_id)+"."+str(stream)
    subscribe_url = IDEAM_base_url +"/subscribe/"+self_id+"/"+str(max_entries)
    subscribe_headers = {"apikey":str(apikey)}
    response = requests.get(url=subscribe_url, headers=subscribe_headers, verify=False)
    s = response.status_code
    if( s == 200):
        return True, response
    else:
        logger.error("subscribe request failed for sender entity {} with status code {} and response {}".format(self_id,s,response.text))
        return False, response


# Share 
def share(self_id, apikey, entity_id, permission):
    """ Approve sharing of data in response to a follow request".

    Arguments:
        self_id   : the id of the entity sending the share request
        apikey    : apikey of the entity sending the share request
        entity_id : id of the entity which is being approved to follow this entity
        permission: can be "read" or "write" or "readwrite
    """

    share_url = IDEAM_base_url +"/share"
    share_headers = {"Content-Type": "application/json", "apikey":str(apikey)}
    data = {"entityID": str(self_id), "permission":permission, "validity": "10D", "requestorID":str(entity_id)}
    response = requests.post(url=share_url, headers=share_headers, data=json.dumps(data), verify=False)
    s = response.status_code
    if( s == 200):
        return True, response
    else:
        logger.error("share request failed for sender entity {} with status code {} and response {}".format(self_id,s,response.text))
        return False, response

# Bind 
def bind(self_id, apikey, entity_id, stream):
    """ Bind to a specified entity or stream.

    Arguments:
        self_id   : the id of the entity sending the bind request
        apikey    : apikey of the entity sending the bind request
        entity_id : id of the target entity to which we wish to bind
        stream    : stream of the target entity to which we wish to bind
    """

    if stream!=None:
        entity_id = str(entity_id)+"."+str(stream)

    bind_url = IDEAM_base_url +"/bind"+"/"+str(self_id)+"/"+str(entity_id)
    bind_headers = {"apikey":str(apikey),"routingKey":"#"}
    response = requests.get(url=bind_url, headers=bind_headers, verify=False)
    s = response.status_code
    if( s == 200):
        return True, response
    else:
        logger.error("bind request failed for sender entity {} with status code {} and response {}".format(self_id,s,response.text))
        return False, response




#=================================================
# Testbench
#=================================================
import time
   
def run_test():

    try:

        # Register device1
        success, device1_apikey = register("device1")
        assert(success)
        print("REGISTER: Registering device1 successful. apikey = {}".format(device1_apikey))
        
        # Register application1
        success, application1_apikey = register("application1")
        assert(success)
        print("REGISTER: Registering application1 successful. apikey = {}".format(application1_apikey))
        
   

        # Let application1 follow device1 (read)
        success = follow("application1", application1_apikey,"device1","read")
        assert(success)
        print("FOLLOW: application1 sent a request to follow(read) device1")
        
        # Let application1 follow device1 (write)
        success = follow("application1", application1_apikey,"device1","write")
        assert(success)
        print("FOLLOW: application1 sent a request to follow(write) device1")

        # Get device1 to check all follow requests forwarded to it
        # and approve each request
        success, response = subscribe("device1","follow", device1_apikey,10)
        assert(success)
        if(success):
            r = response.json()
            for req in r:
                requesting_entity = req["data"]["requestor"]
                permission_sought = req["data"]["permission"]

                print ("FOLLOW: device1 received a follow request from",requesting_entity,"for permission=",permission_sought)
                share_status, share_response = share("device1", device1_apikey, requesting_entity, permission_sought)
                assert(share_status)
                print ("SHARE: device1 sent a share request for entity",requesting_entity,"for permission=",permission_sought)
        
        # Get application1 to check for notifications (responses to its follow request)
        success, response = subscribe("application1","notify", application1_apikey,1)
        assert(success)
        r = response.json()
        assert("Approved" in response.text)
        print ("FOLLOW: application1's follow request was Approved.")
                
        # Get application1 to bind to device1's protected stream
        success, response = bind("application1", application1_apikey, "device1","protected")
        assert(success)
        assert("Bind Queue OK" in response.text)
        print ("BIND: application1 sent a bind request for device1.protected. response=",response.text)

        
        # Get device1 to publish some stuff.
        for i in range (10):
            data = '{"temp": "'+str(100+i)+'"}'
            print("PUBLISH: Publishing from device1. Data=",data)
            success = publish("device1", "protected", device1_apikey, data)
            assert(success)
        

        # Get application1 to print the data it has susbscribed to
        success, response = subscribe(self_id="application1",stream=None, apikey=application1_apikey, max_entries=200)
        assert(success)
        print ("SUBSCRIBE: application1 received the following data from device1:")
        r = response.json()
        for entry in r:
            print(entry)


    finally:        
        print("")
        # De-register device1
        print("DE-REGISTER: De-registering device1: ",end=''),
        success = deregister("device1")
        print("success = ",success)
        
        # De-register application1
        print("DE-REGISTER: De-registering application1: ",end=''),
        success = deregister("application1")
        print("success = ",success)
        return 
  

   
if __name__=='__main__':
    
    logging.basicConfig(level=logging.DEBUG)
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    run_test()
