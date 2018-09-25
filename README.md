# atscale_middleware_testing #

At-scale testing of the ideam middleware using simulated entities.

## REQUIREMENTS ##
* Python3 
* SimPy (https://simpy.readthedocs.io/en/latest/) version > 3.0.10
* IDEAM middleware (https://github.com/rbccps-iisc/ideam) installed on the local machine or a remote server

## USAGE ##

* The routines for communicating with the IDEAM middleware are present at /messaging/ideam_messaging.py. The IP address of the middleware installation is "localhost" by default. This can be changed in the same file.

* To run basic tests for communication with the middleware:
```console
	$ cd messaging
	$ python3 ideam_messaging.py 
	$ python3 setup_entities.py
	$ python3 communication_interface.py
```
* To run tests with simulated devices and apps running in a SimPy environment:
``` console
	$ cd entities
	$ python3 simple_test.py
```
## AUTHOR ##
	Neha Karanjkar (https://github.com/NehaKaranjkar)

