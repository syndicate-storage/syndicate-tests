#!/usr/bin/env python
#
# mkfile.py  --  creates a file with characteristics matching the type specified
#
# mkfile.py <filetype> <filename> [size] [pattern]
#
# DESCRIPTION
#     Create one of the following type of files:
#
#     Types:
#
#     'random'    -- a file with random characters from the set [a-zA-Z0-9]
#     'pattern'   -- a file containing the pattern specified, the pattern is repeated up to the size provided
#     'emptyfile' -- an empty file of zero byte size (i.e. same as "touch")
#     'emptylist' -- a file containing the characters designating an empty list (i.e. "[]")
#
#
#     Options:
#
#         filetype        the type of file to create, as described above
#
#         filename    the name of the file to be created
#
#         size        the size of the file, in bytes
#
#         pattern     when the file type specified is 'pattern', the file will be populated with this pattern
#
#
#     Examples:
#
#         mkfile.py random randfile.txt 4096            (create a random file named randfile.txt of size 4096 bytes)
#
#         mkfile.py pattern pattfile.txt 4096 abc123    (create a 4096 byte file with pattern 'abc123' repeated)
#
#         mkfile.py emptyfile                           (create/touch a zero byte file)


import argparse
import random
import subprocess

# handle arguments
parser = argparse.ArgumentParser()

parser.add_argument('filetype', type=str,
                    help="type of file: random, pattern, emptyfile, emptylist")

parser.add_argument('filename', type=argparse.FileType('w'),
                    help="output filename")

parser.add_argument('size', nargs='?', type=int, default=4096,
                    help="size of file in bytes")

parser.add_argument('pattern', nargs='?', type=str, default='',
                    help="pattern to be repeated")

args = parser.parse_args()

def mkpattern(pattern,size):
    m = len(pattern)
    return "".join([pattern[i % m] for i in range(size)])

def randstring(size):
    pattern = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return "".join([random.choice(pattern) for _ in range(size)])

if args.filetype == "pattern":
    args.filename.write(mkpattern(args.pattern,args.size))
    args.filename.close()
elif args.filetype == "random":
    args.filename.write(randstring(args.size))
    args.filename.close()
elif args.filetype == "emptyfile":
    args.filename.write('')
elif args.filetype == "emptylist":
    args.filename.write("[]\n")
else:
    print "Error: invalid arguments\n"
