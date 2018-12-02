#! python3
#
# Useful routines to register a bunch of entities with the middleware
# and setup the required permissions between them simply by reading a 
# python dictionary containing the system description.

# The system description consists of :
#   1. a list of unique entity names
#   3. a list of permissions, where each permission is 
#      specified as (<requesting entity>, <target entity to be followed>, <permission, which can be"read"/"write">)
#
# This information is to be given as a python dictionary. For example:
#   system_description = {  "entities"       : [ "dev1", "dev2", "appX", "appY"],
#                           "permissions"   : [ ("appX","dev1","read"),("appX","dev1","write"),("appY","dev2","read")]
#                       }
#
# The routines returns True if there were no errors 
# and also returns a python dictionary containing the names of 
# the entities that were registered successfully and their corresponding apikeys.
#
# Author: Neha Karanjkar

from __future__ import print_function 
import corinthian_messaging
import logging
logger = logging.getLogger(__name__)


def deregister_entities(list_of_entity_names):
    """ Takes a list of entity names and 
    deregisters them one-by-one.
    """
    for entity in list_of_entity_names:

	#Admin prefix is not needed since the dict already contains prefixed entity names
        success = corinthian_messaging.deregister(entity)
        logger.debug("DE-REGISTER: de-registering {} successful.".format(entity))

def setup_entities(system_description):
    """ a routine to register a bunch of entities 
    and setup the required permissions between them.
    
    Arguments:
        system_description: a python dictionary containing a list of unique
                        entity names and a list of permissions, where each permission is
                        specified as (<requesting entity>, <target entity to be followed>, <permission>)
                        where permission can be"read"/"write"/"read-write".
                        
        For example:
        system_description = {  "entities"       : [ "dev1", "dev2", "appX", "appY"],
                               "permissions"   : [ ("appX","dev1","read"),("appX","dev1","write"),("appY","dev2","read")]
                           }
     Return Values:
         The routines returns True if there were no errors 
         and also returns a python dictionary containing the names of 
         the entities that were registered successfully and their corresponding apikeys.
     """
    registered_entities = {}
    logger.debug("SETUP: setting up entities and permissions from system description:{}".format(system_description))

    try:

        entities = system_description["entities"]
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
            requestor = p[0]
            target_entity = p[1]
            permission = p[2]
            
            assert(requestor in entities)
            assert(target_entity in entities)
            assert(permission=="read" or permission=="write" or permission=="read-write")
        
        
        # Now register all entities:
        for i in entities:
            apikey = corinthian_messaging.register(i)
            logger.debug("REGISTER: registering entity {} successful. apikey ={} ".format(i,apikey))
            registered_entities["admin/"+i]=apikey

        
        # Set up permissions one-by-one
        for p in permissions:
            requestor = p[0]
            target_entity = p[1]
            permission = p[2]
            
            requestor_apikey = registered_entities["admin/"+requestor]
            target_entity_apikey = registered_entities["admin/"+target_entity]
            
            # send a follow request
            success = corinthian_messaging.follow("admin/"+requestor, requestor_apikey, "admin/"+target_entity, permission)
            logger.debug("FOLLOW: {} sent a follow request to {} for permission {}".format(requestor, target_entity, permission))
            
            # get the target_entity to check the follow request
            messages = corinthian_messaging.follow_requests("admin/"+target_entity, target_entity_apikey,"requests")

	    follow_list = []

	    if permission == "read" or permission == "write":
		follow_list.append(messages.json()[0]["follow-id"])

	    elif permission == "read-write":
		follow_list.append(messages.json()[0]["follow-id"])
		follow_list.append(messages.json()[1]["follow-id"])

            logger.debug("FOLLOW: {} received a follow request from {} for permission {}".format(target_entity,requestor, permission))

            # get the target entitity to approve the follow request using "share" 
	    for follow_id in follow_list:
		success = corinthian_messaging.share("admin/"+target_entity,target_entity_apikey, follow_id)
		
            logger.debug("SHARE: {} sent a share request for entity {} for permission {}".format(target_entity, requestor, permission)) 
            
            # get the requestor to check for the follow notification
	    follow_status_response = corinthian_messaging.follow_requests("admin/"+requestor, requestor_apikey, "status")
	    statuses = follow_status_response.json()
  
	    for status in statuses:
               assert(status["status"] == "approved")

            logger.debug("FOLLOW: follow request made by {} was approved.".format(requestor))
            
	    if permission == "read":
		
		# get the requestor to bind to the target entity's protected stream
		success = corinthian_messaging.bind_unbind("admin/"+requestor, requestor_apikey, "admin/"+target_entity, "#", "protected")
		logger.debug("BIND: {} sent a bind request for {} .".format(requestor, target_entity))
        
        logger.debug("SETUP: done. registered entities: {}".format(registered_entities))
        return True, registered_entities
    
    except Exception as ex:
        logger.error("an exception occurred during setup. Deregistering all entities.") 
	print(ex)
        deregister_entities(entities)
        raise
        


# Testbench:
if __name__=='__main__':
    
    # logging settings:
    logging.basicConfig(level=logging.DEBUG)
    
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("ideam_messaging").setLevel(logging.WARNING)
 
    
    # devices and apps:
    devices = ["device"+str(i) for i in range(2)]
    apps = ["application"+str(i) for i in range (1)]

    system_description = {  "entities"       : devices+apps,
                            "permissions"   : [ (a,d,"read-write") for a in apps for d in devices ]
                        }
    
    success, registered_entities = setup_entities(system_description)
    deregister_entities(registered_entities)
