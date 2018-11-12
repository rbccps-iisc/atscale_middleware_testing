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
logger = logging.getLogger(__name__)



#=========================================
# Middleware settings (constants):
#=========================================

# IP address of the middleware 
CORINTHIAN_ip_address = "localhost"

# url for sending http requests to the apigateway 
CORINTHIAN_base_url = "https://"+CORINTHIAN_ip_address+":8888"

# port number for publish/get using AMQP
CORINTHIAN_port = 5672

# disable SSL check warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# sample schema for registering a streetlight device.
import streetlight_schema
#=========================================





#=========================================
# Routines  using https communications:

def register(entity_id):
    """ Register an entity with the given entity_id.
    NOTE: entity_id can only contain lowercase 
    letters (a-z) or digits (0-9).
    
    Returns:
        True, <apikey> if success, else returns False,None.
    """
    assert(all(c.isdigit() or c.islower() for c in entity_id)), "Illegal entity_id for entity"
    register_url = CORINTHIAN_base_url+ "/register"
    register_headers = {'apikey': 'guest', 'content-type':'application/json'}
    response = requests.post(url=register_url, headers=register_headers, data=streetlight_schema.get_data_from_schema(entity_id), verify=False)
    s = response.status_code
    r = response.json()
    if( s == 200 and r["Registration"] == "success"):
        return True, r["apiKey"]
    else:
        logger.error("registration failed for entity {} with response {}".format(entity_id,response.text))
        return False, None


def deregister(entity_id):
    """ De-register an entity with the given entity_id.
    
    Returns:
        True if success, else returns False.
    """
    deregister_url = CORINTHIAN_base_url+ "/register"
    deregister_headers = {'apikey': 'guest'}
    d = {"id":str(entity_id)}
    response = requests.delete(url=deregister_url, headers=deregister_headers, data = json.dumps(d), verify=False)
    s = response.status_code
    r = response.json()
    if( s == 200 and r["De-Registration"] == "success"):
        return True
    else:
        logger.error("de-registration failed for entity {} with response {}".format(entity_id,response.text))
        return False


# Follow 
def follow(requestor_id, apikey, entity_id, permission):
    """ Send a follow request from <requestor_id> to <entity_id>.
    Arguments:
        requestor_id  : the id of the entity sending the follow request
        apikey        : apikey of the entity sending the follow request
        entity_id     : id of the target entity which we wish to follow
        permission    : can be "read" or "write" or "readwrite"
    Returns:
        True if success, else returns False.
    """
    follow_url = CORINTHIAN_base_url +"/follow"
    follow_headers = {"Content-Type": "application/json", "apikey":str(apikey)}
    data = {"entityID": str(entity_id), "permission":permission, "validity": "10D", "requestorID":str(requestor_id)}
    response = requests.post(url=follow_url, headers=follow_headers, data=json.dumps(data), verify=False)
    s = response.status_code
    if( s == 200):
        return True
    else:
        logger.error("follow request failed for sender entity {} with status code {} and response {}".format(requestor_id,s,response.text))
        return False



# Share 
def share(entity_id, apikey, requestor_id, permission):
    """ Approve sharing of data from <entity_id> 
    in response to a follow request 
    that was made by <requestor_id>.
    
    Arguments:
        entity_id : of the entity who is approving the sharing of its data
        apikey    : apikey of the entity who is approving the sharing of its data
        requestor_id : id of the entity that originally sent a follow request and is being approved to follow
        permission: can be "read" or "write" or "readwrite
    Returns:
        True if success, else returns False.
    """
    share_url = CORINTHIAN_base_url +"/share"
    share_headers = {"Content-Type": "application/json", "apikey":str(apikey)}
    data = {"entityID": str(entity_id), "permission":permission, "validity": "10D", "requestorID":str(requestor_id)}
    response = requests.post(url=share_url, headers=share_headers, data=json.dumps(data), verify=False)
    s = response.status_code
    if( s == 200):
        return True
    else:
        logger.error("share request failed for sender entity {} with status code {} and response {}".format(entity_id,s,response.text))
        return False

# Bind 
def bind(self_id, apikey, entity_id, stream):
    """ Bind the subscribe queue of <self_id> 
    to the specified exchange of <entity_id>,
    so that <self_id> can receive data published by <entity_id>.

    Arguments:
        self_id   : the id of the entity sending the bind request
        apikey    : apikey of the entity sending the bind request
        entity_id : id of the target entity to which we wish to bind
        stream    : stream of the target entity to which we wish to bind. Eg. "public"/"configure" etc
    Returns:
        True if success, else returns False.
    """
    if stream!=None:
        entity_id = str(entity_id)+"."+str(stream)
    bind_url = CORINTHIAN_base_url +"/bind"+"/"+str(self_id)+"/"+str(entity_id)
    bind_headers = {"apikey":str(apikey),"routingKey":"#"}
    response = requests.get(url=bind_url, headers=bind_headers, verify=False)
    s = response.status_code
    if( s == 200 and ("Bind Queue OK" in response.text)):
        return True
    else:
        logger.error("bind request failed for sender entity {} with status code {} and response {}".format(self_id,s,response.text))
        return False

#==========================================
# publish/get using HTTP requests
#==========================================

# Publish
def publish(apikey, exchange, data):
    """ Publish data to a specified entity's exchange.
 
    Arguments:
        apikey    : apikey of the entity that is publishing
        exchange  : exchange to which the data will be published. Eg. "dev0.protected"
        data      : data (json string) to be published.
    Returns:
        True if success, else returns False
    """
    publish_url = CORINTHIAN_base_url +"/publish/"+str(exchange)
    publish_headers = {"apikey":str(apikey)}
    response = requests.post(url=publish_url, headers=publish_headers, data=data, verify=False)
    s = response.status_code
    if( s == 202):
        return True
    else:
        logger.error("publish to exchange {} failed with status code {} and response {}".format(exchange,s,response.text))
        return False


# Get 
def get(apikey, queue, max_entries):
    """ Fetch data from the middleware from a specified queue
    Arguments:
        apikey   : apikey of the entity sending the get request
        queue    : queue from which to fetch messages. Eg "dev0.notify" or "app0" 
        max_entries : max number of entries to fetch at a time.
    Returns:
        True, list of data entries if success, else returns False, None 
    """
    assert(isinstance(max_entries,int))
    get_url = CORINTHIAN_base_url +"/subscribe/"+str(queue)+"/"+str(max_entries)
    get_headers = {"apikey":str(apikey)}
    response = requests.get(url=get_url, headers=get_headers, verify=False)
    s = response.status_code
    if( s == 200):
        data=[]
        r=response.json()
        for req in r:
            data.append(req["data"])
        return True, data
    else:
        return False, None




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
        parameters = pika.ConnectionParameters(CORINTHIAN_ip_address, CORINTHIAN_port, '/', credentials)
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
        parameters = pika.ConnectionParameters(CORINTHIAN_ip_address, CORINTHIAN_port, '/', credentials)
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
        success, messages = get(device1_apikey, "device1.follow", 10)
        assert(success)
        for m in messages:
            requesting_entity = m["requestor"]
            permission_sought = m["permission"]
            print ("FOLLOW: device1 received a follow request from",requesting_entity,"for permission=",permission_sought)
            share_status = share("device1", device1_apikey, requesting_entity, permission_sought)
            assert(share_status)
            print ("SHARE: device1 sent a share request for entity",requesting_entity,"for permission=",permission_sought)
        # Get application1 to check for notifications (responses to its follow request)
        success, messages = get(application1_apikey, "application1.notify", 1)
        assert(success)
        assert("Approved" in str(messages))
        print ("FOLLOW: application1's follow request was Approved.")
                
        # Get application1 to bind to device1's protected stream
        success = bind("application1", application1_apikey, "device1","protected")
        assert(success)
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
            success = publish(device1_apikey, "device1.protected", json.dumps(data))
            assert(success)
        
        # Get application1 to print the data it has susbscribed to
        success, messages = get(application1_apikey, "application1", max_entries=200)
        assert(success)
        print ("SUBSCRIBE: application1 received the following data from device1:")
        for m in messages:
            print(m)
        #=========================================
        
        
        #=========================================
        # Try publish/subscribe using AMQP
        #=========================================
        print ("----------------------------------------")
        print (" Performing publish/get using AMQP ")
        print ("----------------------------------------")
        # Get device1 to publish some stuff.
        device1_channel =  PublishChannel("device1",device1_apikey, "device1.protected")
        for i in range (10):
            data = {}
            data['value']=str(100+i)
            data['using']="amqp"
            print("PUBLISH: Publishing from device1. Data=",data)
            success = device1_channel.publish(json.dumps(data))
            assert(success)
        device1_channel.close()
        
        # Get application1 to print the data it has susbscribed to
        application1_channel = SubscribeChannel("application1",application1_apikey,"application1")
        success, messages = application1_channel.get(max_entries=100)
        assert(success)
        print ("SUBSCRIBE: application1 received the following data from device1:")
        for m in messages:
            print(m)
        application1_channel.close()
        #=========================================
    except:
        print ("An exception occured.")
        raise
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
  
   
if __name__=='__main__':
    
    # set logging level to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)
    
    run_test()
