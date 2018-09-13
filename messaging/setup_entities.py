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


from __future__ import print_function 
from ideam_messaging import *


def deregister_entities(registered_entities):
    """ Takes a python dictionary of the form 
    {"entity1":apikey1, "entity2":apikey2...}
    as argument, and deregisters each entity.
    """
    for entity in registered_entities:
        print("DE-REGISTER: De-registering", entity, end=''),
        success = deregister(entity)
        print(" success = ",success)


def setup_entities(system_description):
    """ a routine to register a bunch of entities 
    and setup the required permissions between them.
    Arguments:
        system_description: a python dictionary containing 
        a list of unique entity names and a list of permissions, 
        where each permission is specified as 
        (<requesting entity>, <target entity to be followed>, <permission, which can be"read"/"write">).
        
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

    try:

        entities = system_description["entities"]
        permissions = system_description["permissions"]

        # Register the entities:
        for i in entities:
            print("REGISTER: Registering",i,end=''),
            success, apikey = register(i)
            if (success) : 
                print(" success = ",success, "apikey = ",apikey)
                registered_entities[i]=apikey
            else:
                raise ValueError("Registration failed")
        
        # Set up permissions
        for p in permissions:
            requestor = p[0]
            target_entity = p[1]
            permission = p[2]
            
            assert(requestor in entities)
            assert(target_entity in entities)
            assert(permission=="read" or permission=="write" or permission=="readwrite")
            requestor_apikey = registered_entities[requestor]
            target_entity_apikey = registered_entities[target_entity]
            
            # send follow requests
            print("FOLLOW:",requestor,"sending a follow request to",target_entity,"for permission=",permission,". ", end='')
            success = follow(requestor, requestor_apikey, target_entity, permission)
            if success:
                print(" success = ",success)
            else:
                raise ValueError("Follow requests failed")
            
            
            # get the target_entity to approve the follow request
            success, response = subscribe(target_entity,"follow", target_entity_apikey,1)
            if(success):
                r = response.json()
                for req in r:
                    requesting_entity = req["data"]["requestor"]
                    permission_sought = req["data"]["permission"]

                print ("FOLLOW: ",target_entity,"received a follow request from",requesting_entity,"for permission=",permission_sought)
                share_status, share_response = share(target_entity,target_entity_apikey, requesting_entity, permission_sought)
                print ("SHARE: ", target_entity, "sent a share request for entity",requesting_entity,"for permission=",permission_sought, end='')
                print (" status=",share_status)
            else:
                raise ValueError("Subscribe requests failed")
                

            # get the requestor to check for notifications 
            success, response = subscribe(requestor,"notify", requestor_apikey,1)
            r = response.json()
            if(success and "Approved" in response.text):
                print ("FOLLOW: app1's follow request was Approved.")
            else:
                raise ValueError("Subscribe requests failed with response"+response.text)
            
            # get the requestor to bind to the target entity's protected stream
            success, response = bind(requestor, requestor_apikey, target_entity,"protected")
            if success:
                print ("BIND:",requestor,"sent a bind request for",target_entity,". success = ",success)
            else:
                raise ValueError("Bind requests failed")

        return True, registered_entities
    
    except Exception as ex:
        print(ex)
        print("ERROR: an exception occurred.")
        print("Deregistering all entities.")
        deregister_entities(registered_entities)
        raise
        


# Testbench:
if __name__=='__main__':
    
    system_description = {  "entities"       : [ "d0","d1","a0","a1"],
                            "permissions"   : [ ("a0","d0","read"),("a0","d0","write"),("a1","d0","read")]
                        }
    
    print("Setting up entities for system description:")
    print(system_description)
    success, registered_entities = setup_entities(system_description)
    print("-----------------------")
    print("Setup done. Registered entities:",registered_entities)
    deregister_entities(registered_entities)
