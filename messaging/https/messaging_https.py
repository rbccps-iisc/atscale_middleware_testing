
from __future__ import print_function 
import requests
import json
import streetlight_schema
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



# IP address of the middleware server
IP_address = "localhost"

# api version
api = "1.0.0"

# urls for sending https requests to teh apigateway 
base_url = "https://"+IP_address+":8443/api/"+api


# Registration
def register(self_id):
    """ Register an entity with the given self_id
    and return (True, <apikey>) if registration succeeds 
    else return (False, 0)."""
    
    register_url = base_url+ "/register"
    register_headers = {'apikey': 'guest', 'content-type':'application/json'}
    response = requests.post(url=register_url, headers=register_headers, data=streetlight_schema.get_data_from_schema(self_id), verify=False)
    r = response.json()
    s = response.status_code
    if( s == 200 and r["Registration"] == "success"):
            return True, r["apiKey"]
    else:
            print ("ERROR: Registration failed for entity",self_id,"with response",response.text)
            return False, 0


# De-registration
def deregister(self_id):
    """ De-register an entity with the given self_id
    and return True if de-registration succeeds else return False."""
    
    deregister_url = base_url+ "/register"
    deregister_headers = {'apikey': 'guest'}
    d = {"id":str(self_id)}
    response = requests.delete(url=deregister_url, headers=deregister_headers, data = json.dumps(d), verify=False)
    r = response.json()
    s = response.status_code
    if( s == 200 and r["De-Registration"] == "success"):
            return True
    else:
            print ("ERROR: De-registration failed for entity",self_id,"with response",response.text)
            return False

# Publish
def publish(self_id, apikey, data, stream):
    """ Publish data from a given entity"""
    
    publish_url = base_url +"/publish/"+self_id+"."+stream
    publish_headers = {"apikey":str(apikey)}
    response = requests.post(url=publish_url, headers=publish_headers, data=data, verify=False)
    s = response.status_code
    if( s == 200):
            return True
    else:
            print ("ERROR: Publish (stream=",stream,") failed for entity",self_id,"with status code",s,"and response", response.text)
            return False, 0


# Follow 
def follow(self_id, apikey, entity_id, permission):
    """ Send a request to follow the data published by a specified entity.
    self_id  : the id of the entity sending the follow request
    apikey   : apikey of the entity sending the follow request
    entity_id: id of the target entity which we wish to follow
    permission: can be "read" or "write" or "readwrite"
    """

    follow_url = base_url +"/follow"
    follow_headers = {"Content-Type": "application/json", "apikey":str(apikey)}
    data = {"entityID": str(entity_id), "permission":permission, "validity": "10D", "requestorID":str(self_id)}
    response = requests.post(url=follow_url, headers=follow_headers, data=json.dumps(data), verify=False)
    s = response.status_code
    if( s == 200):
            return True
    else:
            print ("ERROR: Follow request failed for sender entity",self_id,"with status code",s,"and response", response.text)
            return False, 0

# Subscribe 
def subscribe(self_id, apikey, max_entries):
    """ Fetch data from the middleware meant for this entity
    self_id  : the id of the entity/stream from which to fetch data 
    apikey   : apikey of the entity sending the subscribe request
    max_entries : max number of entries to fetch at a time
    """
    subscribe_url = base_url +"/subscribe/"+str(self_id)+"/"+str(max_entries)
    subscribe_headers = {"apikey":str(apikey)}
    response = requests.get(url=subscribe_url, headers=subscribe_headers, verify=False)
    s = response.status_code
    if( s == 200):
            return True, response
    else:
            print ("ERROR: Follow request failed for sender entity",self_id,"with status code",s,"and response", response.text)
            return False, response

# Share 
def share(self_id, apikey, entity_id, permission):
    """ Approve sharing of data in response to a follow request".
    self_id   : the id of the entity sending the share request
    apikey    : apikey of the entity sending the share request
    entity_id : id of the entity which is being approved to follow this entity
    permission: can be "read" or "write" or "readwrite
    """

    share_url = base_url +"/share"
    share_headers = {"Content-Type": "application/json", "apikey":str(apikey)}
    data = {"entityID": str(self_id), "permission":permission, "validity": "10D", "requestorID":str(entity_id)}
    response = requests.post(url=share_url, headers=share_headers, data=json.dumps(data), verify=False)
    s = response.status_code
    if( s == 200):
            return True, response
    else:
            print ("ERROR: Share request failed for sender entity",self_id,"with status code",s,"and response", response.text)
            return False, response

# Bind 
def bind(self_id, apikey, entity_id):
    """ Bind to a specified entity or stream.
    self_id   : the id of the entity sending the bind request
    apikey    : apikey of the entity sending the bind request
    entity_id : id of the entity or stream to which we wish to bind
    """

    bind_url = base_url +"/bind"+"/"+str(self_id)+"/"+str(entity_id)
    bind_headers = {"apikey":str(apikey),"routingKey":"#"}
    response = requests.get(url=bind_url, headers=bind_headers, verify=False)
    s = response.status_code
    if( s == 200):
            return True, response
    else:
            print ("ERROR: Bind request failed for sender entity",self_id,"with status code",s,"and response", response.text)
            return False, response




#=================================================
import time


# Testbench

    
   
def run_test():

    # Register device1
    print("REGISTER: Registering device1: ",end=''),
    success, device1_apikey = register("device1")
    print("success = ",success, "apikey = ",device1_apikey)
    
    # Register app1
    print("REGISTER: Registering app1: ",end=''),
    success, app1_apikey = register("app1")
    print("success = ",success, "apikey = ",app1_apikey)
    
   


    # Let app1 follow device1 (read)
    print("FOLLOW: app1 sent a request to follow(read) device1: ",end=''),
    success = follow("app1", app1_apikey,"device1","read")
    print("success = ",success)
    
    # Let app1 follow device1 (write)
    print("FOLLOW: app1 sent a request to follow(write) device1: ",end=''),
    success = follow("app1", app1_apikey,"device1","write")
    print("success = ",success)

    time.sleep(2)
   
   
    # Get device1 to check all follow requests forwarded to it
    # and approve each request
    success, response = subscribe("device1.follow", device1_apikey,10)
    if(success):
        r = response.json()
        for req in r:
            requesting_entity = req["data"]["requestor"]
            permission_sought = req["data"]["permission"]

            print ("FOLLOW: device1 received a follow request from",requesting_entity,"for permission=",permission_sought)
            share_status, share_response = share("device1", device1_apikey, requesting_entity, permission_sought)
            print ("SHARE: device1 sent a share request for entity",requesting_entity,"for permission=",permission_sought, end='')
            print (" status=",share_status)
    
    # Get app1 to check for notifications (responses to its follow request)
    success, response = subscribe("app1.notify", app1_apikey,1)
    if(success):
        r = response.json()
        if ("Approved" in response.text):
            print ("FOLLOW: app1's follow request was Approved.")
        else:
            print ("FOLLOW: app1's follow request was *Not* Approved.")
            
    # Get app1 to bind to device1's protected stream
    success, response = bind("app1", app1_apikey, "device1.protected")
    print ("BIND: app1 sent a bind request for device1.protected. success = ",success,"response=",response.text)

    
    # Get device1 to publish some stuff.
    for i in range (10):
        data = '{"temp": "'+str(100+i)+'"}'
        print("PUBLISH: Publishing from device1. Data=",data,".",end=''),
        success = publish("device1", device1_apikey,data,"protected")
        print("success = ",success)
   
    time.sleep(1)
    # Get app1 to print the data it has susbscribed to
    success, response = subscribe("app1", app1_apikey,20)
    if(success):
        print ("SUBSCRIBE: app1 received the following data from device1:")
        r = response.json()
        for entry in r:
            print(entry["data"]["temp"]," ",end='')
    
    print("")
    # De-register device1
    print("DE-REGISTER: De-registering device1: ",end=''),
    success = deregister("device1")
    print("success = ",success)
    
    # De-register app1
    print("DE-REGISTER: De-registering app1: ",end=''),
    success = deregister("app1")
    print("success = ",success)
    return 

    
if __name__=='__main__':
    run_test()
