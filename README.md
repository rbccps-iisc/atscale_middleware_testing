# atscale_middleware_testing

At-scale testing of the ideam middleware using simulated entities.

REQUIREMENTS:
	python3 (tested with version 3.5.2)
	SimPy (https://simpy.readthedocs.io/en/latest/)
		tested with version 3.0.10
	ideam middleware (installed on local machine or remote server)
	
AUTHOR:
	Neha Karanjkar

USAGE:
	1. The routines for communicating with the ideam middleware
	are present at /messaging/ideam_messaging.py.
	The IP address of the middleware installation is "localhost" 
	by default. This can be changed in the same file.

	2. To run basic tests for communication with the middleware:
	$ cd messaging
	$ python3 ideam_messaging.py 
	$ python3 setup_entities.py
	$ python3 communication_interface.py

	3. To run tests with app and device models simulated using SimPY:
	$ cd entities
	$ python3 simple_test.py




	
