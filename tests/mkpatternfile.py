#!/usr/bin/env python
# mkrandfile.py
# Creates a file of a certain size with characters from the set [a-zA-Z0-9]

import argparse

# handle arguments
parser = argparse.ArgumentParser()

parser.add_argument('filename', type=argparse.FileType('w'),
                    help="output filename")

parser.add_argument('size', type=int, default=4096,
                    help="size of file in bytes")

parser.add_argument('pattern', type=str,
                    help="pattern to be repeated")

args = parser.parse_args()

def mkpattern(pattern,size):
    m = len(pattern)
    return "".join([pattern[i % m] for i in range(size)])

args.filename.write(mkpattern(args.pattern,args.size))
args.filename.close()

