#!python3

# SimPy model for a smart streetlight.
#
# SENSORS:
#	ambient_light_level (0-1) Ambient light intensity
#	led_output_level	(0-1) Output level of the LED. 1 => max brightness, 0=> OFF
#	activity_detected	(True/False) Whether activity was detected.
#
# BEHAVIOR:
#		1. Periodically publish sensor data
#		2. Adjust led_output_level as per ambient_light_level
#
# Author: Neha Karanjkar

import sys
import simpy
import json
import logging
logger = logging.getLogger(__name__)

# Interfaces for communication with the middleware
sys.path.insert(0, '../messaging')
import communication_interface


class StreetlightDevice(object):
	
	def __init__(self, env, ID, apikey):
		self.env = env
		self.ID = ID         # unique identifier for the device
		self.apikey = apikey # apikey required for authentication
		self.period = 1      # operational period for the device (in seconds)
		self.state = "NORMAL"# state of the device. Can be "NORMAL" or "FAULT"

		# sensor values:
		self.ambient_light_level =0
		self.led_output_level =0
		self.activity_detected=False
				
		# interface for publishing data:
		self.publish_thread = communication_interface.PublishInterface(self.ID, self.apikey)
		self.publish_count =0
		
		# interface for receiving commands:
		self.receive_commands_thread = communication_interface.ReceiveCommandsInterface(self.ID, self.apikey)
		    
		# start a simpy process for the main device behavior
		self.behavior_process=self.env.process(self.behavior())
		
	
	def check_commands(self):
		if not self.receive_commands_thread.queue.empty():
			while (not self.receive_commands_thread.queue.empty()):
				cmd = self.receive_commands_thread.queue.get()
				logger.debug("SIM_TIME:{} ENTITY:{} received command {}.".format(self.env.now, self.ID, cmd))


	def adjust_led_output_level(self):
		if(self.ambient_light_level >= 0.8):
			# Light is OFF during daytime
			self.led_output_level = 0
		elif(self.activity_detected == False)
			# Light is dimmed at night when no activity is detected
			self.led_output_level = 0.3
		else:
			# Light is bright when activity is detected
			self.led_output_level = 1

	def publish_sensor_data(self):
		data = json.dumps({ "ambient_light_level": self.ambient_light_level,
							"led_output_level": self.led_output_level,
							"activity_detected": self.activity_detected
							})
		self.publish_thread.publish(data)
		self.publish_count+=1
		logger.debug("SIM_TIME:{} ENTITY:{} published data {}".format(self.env.now, self.ID, data))
	
	
	# main behavior of the device:
	def behavior(self):
		while (True): # the main loop.
			try:
				#---------------------------
				# NORMAL STATE
				#---------------------------
				if self.state == "NORMAL":
					
					# check if there are commands from the app
					self.check_commands()
					
					# adjust led brightness as per ambient light 
					# and activity sensed
					self.adjust_led_output_level()
					
					# publish sensor data to middleware
					self.publish_sensor_data()
							
					# wait till the next clock cycle
					yield self.env.timeout(self.period)
					
				#---------------------------
				# FAULT STATE
				#---------------------------
				elif self.state == "FAULT":
					logger.info("SIM_TIME:{} ENTITY:{} entered the FAULT state.".format(self.env.now, self.ID))
					# send a "fault" status to the app
					self.publish_thread.publish(json.dumps({"status":"FAULT"}))
					# keep waiting for a "resume" response from the app
					self.resume_command_received = False
					while(not self.resume_command_received):
						if not self.receive_commands_thread.queue.empty():
							while (not self.receive_commands_thread.queue.empty()):
								cmd = self.receive_commands_thread.queue.get()
								logger.debug("SIM_TIME:{} ENTITY:{} received command {}.".format(self.env.now, self.ID, cmd))
								assert("command" in cmd["data"])
								if (cmd["data"]["command"]=="RESUME"):
									self.resume_command_received=True
						# wait till the next clock cycle
						yield self.env.timeout(self.period)
					# resume command received.
					# go back to normal state.
					self.state="NORMAL"
					  
				else:
					assert(0),"Invalid device state"
					
			except simpy.Interrupt as i:
				# a simpy interrupt occured.
				# check that this was a fault injected.
				logger.info("SIM_TIME:{} ENTITY:{} was interrupted because of {}".format(self.env.now, self.ID,i.cause))
				
				# go into fault state.
				if i.cause=="FAULT":
					self.state="FAULT"
				    
	# stop all communication threads
	def end(self):
		self.publish_thread.stop()
		self.receive_commands_thread.stop()
		logger.info("SIM_TIME:{} ENTITY:{} stopping.".format(self.env.now, self.ID))
