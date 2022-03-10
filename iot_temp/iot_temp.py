#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Monitor the current temperature via a w1 device and feed the values to
io.adafruit (AIO).  This runs under the Raspberry Pi (Linux) OS.

Assumptions:
    *  Environment variables IO_USERNAME, IO_KEY contain AIO credentials.
    *  SSL certificates are installed (ca-certificates debian package)
"""


import glob, os, socket, sys, time

try:
    from Adafruit_IO import Client
except ImportError:
    sys.exit("AIO support is missing; please do: pip3 install adafruit-io")


# read some parameters from the environment
try:
    usernm = os.environ["IO_USERNAME"]
    passwd = os.environ["IO_KEY"]
except KeyError:
    sys.exit('Missing AIO Credentials: set environment variables "IO_KEY", "IO_USERNAME"')

# publish to a feed called: <hostname>-temp
my_feed = "{}-temp".format(socket.gethostname())

# parameters to control how frequently we report a temperature
min_temp_change = 0.2  # only report if changed this much from last_temp
aio_delay = 30  # seconds to sleep after sending to AIO
retry_delay = 1  # seconds to delay before retry upon error

# parameters to control logging
log_enable = False
log_to = sys.stderr


def log(*msg):
    "print out diagnostic messages prepended with a timestamp"
    if log_enable:
        now = time.strftime("%a %F %T", time.localtime())
        print(now, end=" ", file=log_to)
        print(*msg, file=log_to)


def read_temp_raw():
    "return the raw reading string from the first w1 temp sensor found"
    pattern = "/sys/bus/w1/devices/28*/w1_slave"
    device_file = glob.glob(pattern)[0]
    with open(device_file, "r") as f:
        reading = f.readlines()
    return reading


def read_temp():
    "return temperature in degrees C and F as a tuple of floats, or None on failure"
    lines = read_temp_raw()
    if lines[0].strip()[-3:] == "YES":
        equals_pos = lines[1].find("t=")
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2 :]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0
            return temp_c, temp_f
    # return None if control reaches here


def report_temps():
    "the main polling loop to read temp and send to AIO"
    aio = Client(usernm, passwd)  # instantiate client
    last_temp = -1000
    while True:
        try:
            temp_c, temp_f = read_temp()
            # report temp only if it has changed since the last reading ...
            if abs(temp_f - last_temp) >= min_temp_change:
                temp_str = "{:.1f}".format(temp_f)
                log(temp_str + "°F")
                aio.send(my_feed, temp_str)  # net problems can cause fail
                last_temp = temp_f  # note that reading got to AIO
            time.sleep(aio_delay)  # limits AIO update rate
        except:
            time.sleep(retry_delay)  # limits error retry rate


if __name__ == "__main__":
    sys.exit(report_temps())
