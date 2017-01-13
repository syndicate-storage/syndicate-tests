#!/usr/bin/env python
# waitgateway.py
# wait until syndicate gateway is ready

import argparse
import sys
import os
import time
import requests

def exit_success(msg):
    sys.stderr.write("SUCCESS: %s\n" % msg)
    sys.stderr.write("Exit with code 0\n")
    sys.exit(0)

def exit_fail(msg):
    sys.stderr.write("FAIL: %s\n" % msg)
    sys.stderr.write("Exit with code 1\n")
    sys.exit(1)

def gateway_ping(hostname, portnum, attempts):
    for i in xrange(0, attempts):
        try:
            req = requests.get("http://%s:%d/PING" % (hostname, portnum))
            if req.status_code == 200:
                return True
            else:
                # something happened
                return False
        except:
            # wait
            time.sleep(1.0)
    return False

# handle arguments
parser = argparse.ArgumentParser()

parser.add_argument('hostname', help="hostname")
parser.add_argument('portnum', help="portnum")
parser.add_argument('timeout', help="timeout")

args = parser.parse_args()

hostname = args.hostname
portnum = int(args.portnum)
timeout = int(args.timeout)

ping = gateway_ping(hostname, portnum, timeout)
if ping:
    exit_success("gateway is online - %s:%d" % (hostname, portnum))
else:
    exit_fail("gateway is offline - %s:%d" % (hostname, portnum))
