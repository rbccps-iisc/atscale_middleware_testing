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
from ideam_messaging import *
import logging
logger = logging.getLogger(__name__)


def deregister_entities(list_of_entity_names):
    """ Takes a list of entity names and 
    deregisters them one-by-one.
    """
    for entity in list_of_entity_names:
        success = deregister(entity)
        if(success):
            logger.debug("DE-REGISTER: de-registering {} successful.".format(entity))
        assert(success)


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
            success, apikey = register(i)
            assert (success)
            logger.debug("REGISTER: registering entity {} successful. apikey ={} ".format(i,apikey))
            registered_entities[i]=apikey

        
        # Set up permissions one-by-one
        for p in permissions:
            requestor = p[0]
            target_entity = p[1]
            permission = p[2]
            
            requestor_apikey = registered_entities[requestor]
            target_entity_apikey = registered_entities[target_entity]
            
            # send a follow request
            success = follow(requestor, requestor_apikey, target_entity, permission)
            assert(success)
            logger.debug("FOLLOW: {} sent a follow request to {} for permission {}".format(requestor, target_entity, permission))
            time.sleep(0.1)
            
            # get the target_entity to check the follow request
            success, response = subscribe(target_entity,"follow", target_entity_apikey,1)
            assert(success)
            r = response.json()
            assert (len(r)>0) and ("data" in r[0])
            assert("requestor" in r[0]["data"])
            assert("permission" in r[0]["data"])

            req = r[0]
            requesting_entity = req["data"]["requestor"]
            permission_sought = req["data"]["permission"]
            logger.debug("FOLLOW: {} received a follow request from {} for permission {}".format(target_entity,requesting_entity,permission_sought))

            # get the target entitity to approve the follow request using "share" 
            success, response = share(target_entity,target_entity_apikey, requesting_entity, permission_sought)
            assert(success)
            logger.debug("SHARE: {} sent a share request for entity {} for permission {}".format(target_entity, requesting_entity,permission_sought)) 
            
            # get the requestor to check for the follow notification
            success, response = subscribe(requestor,"notify", requestor_apikey,1)
            assert(success)
            r = response.json()
            assert("Approved" in response.text)
            logger.debug("FOLLOW: follow request made by {} was approved.".format(requestor))
            
            # get the requestor to bind to the target entity's protected stream
            success, response = bind(requestor, requestor_apikey, target_entity,"protected")
            assert(success)
            logger.debug("BIND: {} sent a bind request for {} .".format(requestor, target_entity))

        
        logger.debug("SETUP DONE: registered entities: {}".format(registered_entities))
        return True, registered_entities
    
    except Exception as ex:
        logger.error("an exception occurred during setup. Deregistering all entities.") 
        deregister_entities(entities)
        raise
        


# Testbench:
if __name__=='__main__':
    
    # logging settings:
    logging.basicConfig(level=logging.DEBUG)
    # suppress debug messages from other modules used.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
 
    
    # devices and apps:
    devices = ["device"+str(i) for i in range(4)]
    apps = ["app"+str(i) for i in range (1)]

    system_description = {  "entities"       : devices+apps,
                            "permissions"   : [ (a,d,"read") for a in apps for d in devices ]
                        }
    
    success, registered_entities = setup_entities(system_description)
    deregister_entities(registered_entities)
