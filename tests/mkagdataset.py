#!/usr/bin/env python
# mkrandfile.py
# Creates a file of a certain size with characters from the set [a-zA-Z0-9]

import argparse
import base64
import json
import os
import shutil
import syndicate.util.objects as synobj

# handle arguments
parser = argparse.ArgumentParser()

parser.add_argument('driver_path', type=str,
                    help="syndicate ag driver path")

parser.add_argument('--secrets', dest='secrets', action='store_true')
parser.add_argument('--no-secrets', dest='secrets', action='store_false')
parser.set_defaults(secrets=False)

parser.add_argument('gw_privkey_pem', type=str,
                    help="gateway privkey pem")

args = parser.parse_args()

# create AG source dataset.  extract config
ag_driver = synobj.load_driver( args.driver_path, args.gw_privkey_pem, args.secrets )
assert 'config' in ag_driver
ag_config_txt = base64.b64decode(ag_driver['config'])
ag_config = json.loads(ag_config_txt)

# path to file...
assert 'DATASET_DIR' in ag_config
testdir = ag_config['DATASET_DIR']
if os.path.exists(testdir):
    shutil.rmtree(testdir)

os.makedirs(testdir)
