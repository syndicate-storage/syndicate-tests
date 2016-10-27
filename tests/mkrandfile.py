#!/usr/bin/env python
# mkrandfile.py
# Creates a file of a certain size with characters from the set [a-zA-Z0-9]

import argparse
import random

# handle arguments
parser = argparse.ArgumentParser()

parser.add_argument('filename', type=argparse.FileType('w'),
                    help="output filename")

parser.add_argument('size', type=int, default=4096,
                    help="size of file in bytes")

args = parser.parse_args()


def randstring(size):
    pattern = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return "".join([random.choice(pattern) for _ in range(size)])

args.filename.write(randstring(args.size))
args.filename.close()

