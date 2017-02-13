import sys
import argparse
import logging
import json
import re
from subprocess import Popen, PIPE

from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory
from pubnub.enums import PNReconnectionPolicy
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

release_subscribe_key = "sub-c-3c3c9c40-e9dd-11e6-b325-02ee2ddab7fe";
release_publish_key = "pub-c-cdafa971-87da-4fab-b15b-fc71f59b763b"

control_channel = "vfa_remote_mode_control_channel_"
data_channel = "vfa_remote_mode_data_channel_"


bt_dev_list = []
pubnub = ""
scanning = False

def bt_address_publish_callback(envelope, status):
     	if not status.is_error():
              	logging.info("Data sent successfully to app")
         	pass
      	else:
           	logging.error("Error sending data")
           	pass

def publish_bt_address_to_data_channel(bt_addr):
	global bt_dev_list
	if bt_addr in bt_dev_list:
		return;

	bt_dev_list.append(bt_addr)
	new_msg = {}
	new_msg["data_type"] = 1
	new_msg["data"] = bt_addr
	
	pubnub.publish().channel(data_channel).message(new_msg).async(bt_address_publish_callback)
	logging.info("Data published to data channel: %s", str(new_msg))	
	
def start_le_scan():
	proc = Popen(["timeout", "-s", "SIGINT", "5s", "hcitool", "lescan"], stdout=PIPE)
	while True:
		line = proc.stdout.readline()
		if line != '':
			line_parts = line.split(" ")
			#regex expression to check valid mac-address
			#taken form here: http://stackoverflow.com/a/7629690
			if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", line_parts[0].lower()):
				print "Device found: ", line_parts[0] 
				publish_bt_address_to_data_channel(line_parts[0])
	
		else:
			global scanning
			scanning = False
			global bt_dev_list
			bt_dev_list[:] = []
			break

def process_message(message):
	try:
		command = message["command"];
		if command == 1:
			global scanning
			scanning = True
			print "Scan command received from app"
			start_le_scan()
	except:
		print "Invalid command received"

class MySubscribeCallback(SubscribeCallback):
	def presence(self, pubnub, presence):
         	pass  # handle incoming presence data

      	def status(self, pubnub, status):
		if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
        	       	logging.info("Internet connectivity lost")

       	        elif status.category == PNStatusCategory.PNConnectedCategory:
                 	print "Subscription successful"

              	elif status.category == PNStatusCategory.PNReconnectedCategory:
                  	logging.info("Reconnected to Internet")

             	elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
                  	logging.info("Decryption error")

    	def message(self, pubnub, message):
		logging.info("Message received: %s", str(message.message))
		global scanning
		if not scanning:
              		process_message(message.message)
	

def check_command_line_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("-v", "--verbose", help="increase output verbosity (pubnub + wispero)", action="store_true")
	
	args = parser.parse_args()
	if args.verbose:
		print "verbosity turned on"
		logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)	
		

def configure_pubnub(subscribe_key, publish_key):
	pnconfig = PNConfiguration()
      	pnconfig.subscribe_key = subscribe_key
      	pnconfig.publish_key = publish_key
	pnconfig.origin = "pubsub.pubnub.com"
	pnconfig.reconnection_policy = PNReconnectionPolicy.LINEAR	

	global pubnub
     	pubnub = PubNub(pnconfig)
	print "Pubnub configured"

def take_user_input_and_set_channel_names():
	print "Enter your credentials:"
	email = raw_input("E-mail: ")
	secret_key = raw_input("Secret Key: ")
	
	global control_channel
	global data_channel
	
	control_channel += email + "_" + secret_key
	data_channel += email + "_" + secret_key

	logging.debug("Control channel: %s", control_channel)
	logging.info("Data channel: %s", data_channel)

def subscribe_to_control_channel():
	global control_channel
	global data_channel
	
	pubnub.add_listener(MySubscribeCallback())
	pubnub.subscribe().channels(control_channel).execute()
	logging.info("Subscribing to control channel")


if __name__ == "__main__":
	check_command_line_args()
	configure_pubnub(release_subscribe_key, release_publish_key)

	take_user_input_and_set_channel_names()	
	subscribe_to_control_channel()
	

