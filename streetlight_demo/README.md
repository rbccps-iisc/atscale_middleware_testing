# A demo for smart streetlights.

A smart streetlight adapts to changes in ambient light and presence/absence of activity. It turns OFF automatically during the daytime and stays dimmed at night when no activity is detected near it. When a streetlight detects activity (such as a pedestrian) in its vicinity, it brightens up and also publishes a status message about this activity detected to the middleware.

An app that controls all of the streetlights subscribes to all sensor data and status messages from the streetlights. It maintains a snapshot of the latest sensor data received. When no messages are received from a streetlight for a certain amount of time, the device is marked as being 'possibly faulty'. When the app receives a status message from a streetlight about activity detected, it sends a command to the neighbouring streetlights, in-turn causing them to brighten up in anticipation of a pedestrian/vehicle moving in that direction.

To run the demo:

 * First, set up registrations and permissions with the middleware for a specified number of streetlight devices.
``` console
	$ ./do_setup.py
```
 * Then, run the simulation for a specified amount of time:
``` console
	$ ./run_simulation.py
```
 * To de-register all the streetlight entities in the middleware:
``` console
	$ ./do_deregistrations.py
```


