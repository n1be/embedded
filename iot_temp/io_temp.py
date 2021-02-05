#!/usr/bin/python3
# -*- coding: utf-8 -*-
""""Read the current temperature from a w1 device and feed the value to
io.adafruit (AIO).

Assumptions:
    *  Environment variables IO_USERNAME, IO_KEY contain AIO credentials.
    *  SSL certificates are installed (ca-certificates debian package)
"""


import glob, os, socket, sys, time
try:
    from Adafruit_IO import Client
except ImportError:
    sys.exit( "AIO support is missing; please do: pip3 install adafruit-io")


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


# parameters to control how frequently we report a temperature
last_temp = -1000
min_temp_change = 0.2   # only report if changed this much from last_temp
delay = 15              # seconds to wait before checking temperature again

# parameters
usernm = os.environ["IO_USERNAME"]
passwd = os.environ["IO_KEY"]
my_feed = "{}-temp".format( socket.gethostname()) 

# instantiate client
aio = Client( usernm, passwd)

while True:
    temp_c, temp_f = read_temp()
    # report temp only if it has changed since the last reading ...
    if abs( temp_f - last_temp) >= min_temp_change:
        temp_str = "{:.1f}".format( temp_f)
        # print( now(), temp_str + "°F")
        try:
            aio.send( my_feed, temp_str)    # net problems can cause fail
            last_temp = temp_f
        except:
            pass
    time.sleep( delay) # limits update rate

