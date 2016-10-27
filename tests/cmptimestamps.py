#!/usr/bin/env python
# cmptimestamps.py
# compare two timestamps

import argparse
import sys

def exit_success(msg):
    sys.stderr.write("SUCCESS: %s\n" % msg)
    sys.stderr.write("Exit with code 0\n")
    sys.exit(0)

def exit_inputfail(msg):
    sys.stderr.write("INPUTFAIL: %s\n" % msg)
    sys.stderr.write("Exit with code 2\n")
    sys.exit(2)

def exit_fail(msg):
    sys.stderr.write("FAIL: %s\n" % msg)
    sys.stderr.write("Exit with code 1\n")
    sys.exit(1)

# handle arguments
parser = argparse.ArgumentParser()

parser.add_argument('op', help="operation")
parser.add_argument('-f', help="read from file",
                    action="store_true")
parser.add_argument('t1', help="timestamp1")
parser.add_argument('t2', help="timestamp2")

args = parser.parse_args()

t1s = ""
t2s = ""
if args.f:
    # read from files
    with open(args.t1, 'r') as f1:
        for line in f1:
            t1s = line.strip()
            break

    with open(args.t2, 'r') as f2:
        for line in f2:
            t2s = line.strip()
            break;
else:
    t1s = args.t1
    t2s = args.t2

if not t1s.isdigit():
    exit_inputfail("the first parameter is not digits")

if not t2s.isdigit():
    exit_inputfail("the second parameter is not digits")

t1 = int(t1s)
t2 = int(t2s)

if args.op in ["eq", "EQ"]:
    if t1 == t2:
        exit_success("%d == %d" % (t1, t2))
    else:
        exit_fail("%d == %d" % (t1, t2))
elif args.op in ["neq", "NEQ"]:
    if t1 != t2:
        exit_success("%d != %d" % (t1, t2))
    else:
        exit_fail("%d != %d" % (t1, t2))
elif args.op in ["lt", "LT"]:
    if t1 < t2:
        exit_success("%d < %d" % (t1, t2))
    else:
        exit_fail("%d < %d" % (t1, t2))
elif args.op in ["le", "LE"]:
    if t1 <= t2:
        exit_success("%d <= %d" % (t1, t2))
    else:
        exit_fail("%d <= %d" % (t1, t2))
elif args.op in ["gt", "GT"]:
    if t1 > t2:
        exit_success("%d > %d" % (t1, t2))
    else:
        exit_fail("%d > %d" % (t1, t2))
elif args.op in ["ge", "GE"]:
    if t1 >= t2:
        exit_success("%d >= %d" % (t1, t2))
    else:
        exit_fail("%d >= %d" % (t1, t2))
else:
    exit_fail("unknown operator %s" % args.op)
