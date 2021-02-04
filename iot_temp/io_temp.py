#!/usr/bin/python3
# -*- coding: utf-8 -*-
""""Read the current temperature from a w1 device and feed the value to
io.adafruit (AIO) via MQTT using TLS.

Assumptions:
    *  Environment variables IO_USERNAME, IO_KEY contain AIO credentials.
    *  SSL certificates are installed (ca-certificates debian package)
"""


import glob, os, socket, sys, time
try:
    import paho.mqtt.client as mqtt
except ImportError:
    sys.exit( "MQTT support is missing; please install: python3-paho-mqtt")


def read_temp_raw():
    "return a raw reading string from the first w1 sensor found"
    try:
        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'
    except:
        # Possible no sys file if nodev or driver not loaded
        return None
    with open( device_file, 'r') as f:
        lines = f.readlines()
    return lines

def read_temp():
    "return temperature in degrees C and F as a tuple of floats"
    lines = read_temp_raw()
    while (not lines) or lines[0].strip()[-3:] != 'YES':
        # retry if did not get a valid reading
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f
    # by default, return None if "t=" was not in the string

def now():
    "Return the current date/time as a string"
    return time.strftime( "%a %F %T", time.localtime(time.time()))

def on_connect(client, userdata, flags, rc, properties=None):
    "Callback to log connect"
    print(now(), "Connected With Result Code: {}".format(rc))

def on_disconnect(client, userdata, rc):
    "Callback to log and handle disconnect"
    client.loop_stop()
    sys.exit( "{} Client Got Disconnected, rc:{}".format( now, rc))


# parameters to control how frequently we report a temperature
last_temp = -1000
min_temp_change = 0.2   # only report if changed this much from last_temp
delay = 15              # seconds to wait before checking temperature again

# MQTT parameters
broker_host = "io.adafruit.com"
broker_port = 1883 # 8883 for ssl
usernm = os.environ["IO_USERNAME"]
passwd = os.environ["IO_KEY"]
my_feed = "{}-temp".format( socket.gethostname()) 
topic = "{}/f/{}".format( usernm, my_feed)

# instantiate client, make settings needed, finally connect to broker
client = mqtt.Client( client_id=my_feed)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.username_pw_set( usernm, passwd)
# Not for AIO ...
# client.will_set( topic, "Offline", qos=1)
#
# a few more settings needed for TLS
broker_port = 8883 # 8883 for ssl
client.tls_set_context()
#
client.connect(broker_host, broker_port)
client.loop_start() # run MQTT I/O in another thread

while True:
    temp_c, temp_f = read_temp()
    # report temp only if it has changed since the last reading ...
    if abs( temp_f - last_temp) >= min_temp_change:
        last_temp = temp_f
        temp_str = "{:.1f}".format( temp_f)
        # print( now(), temp_str + "°F")
        client.publish( topic, temp_str)
    time.sleep( delay) # limits update rate

