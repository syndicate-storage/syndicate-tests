#!/usr/bin/env python
# waitfusemount.py
# wait until fuse mount succeeds

import argparse
import sys
import psutil
import os
import time

def exit_success(msg):
    sys.stderr.write("SUCCESS: %s\n" % msg)
    sys.stderr.write("Exit with code 0\n")
    sys.exit(0)

def exit_fail(msg):
    sys.stderr.write("FAIL: %s\n" % msg)
    sys.stderr.write("Exit with code 1\n")
    sys.exit(1)

def get_processes(name):
    matching_processes = []
    for p in psutil.process_iter():
        try:
            if p.name == name:
                matching_processes.append(p)
        except psutil.NoSuchProcess:
            pass
    return matching_processes
    
def get_mounts(name, path):
    matching_mounts = []
    with open('/proc/mounts', 'r') as f:
        for line in f:
            l = line.strip()
            w = l.split()
            if w[2].startswith("fuse."):
                if w[0] == name and w[1] == path:
                    matching_mounts.append(w)
    return matching_mounts

# handle arguments
parser = argparse.ArgumentParser()

parser.add_argument('app_name', help="app name")
parser.add_argument('mount_path', help="mountpath")
parser.add_argument('timeout', help="timeout")

args = parser.parse_args()

app_name = args.app_name
mount_path = os.path.abspath(args.mount_path)
timeout = int(args.timeout)

tick = 0
while True:
    # check processes
    matching_processes = get_processes(app_name)
    if len(matching_processes) == 0:
        exit_fail("cannot find matching processes - %s" % (app_name))

    # check mount
    matching_mounts = get_mounts(app_name, mount_path)
    if len(matching_mounts) != 0:
        for m in matching_mounts:
            print m
        exit_success("fuse is successfully mounted - %s / %s" % (app_name, mount_path))

    time.sleep(1)
    tick += 1
    
    if tick >= timeout:
        exit_fail("mount timed out - %s / %s" % (app_name, mount_path))
