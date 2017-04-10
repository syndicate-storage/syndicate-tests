#!/bin/bash

USERNAME=$1
VOLUMENAME=$2
VOLUMEDESCRIPTION=$3
BLOCKSIZE=$4
GATEWAYTYPE=$5
GATEWAYPORT=$6
HOSTNAME=$7
OUTPUTFILE=$8


cat <<'EOF' | sed -e s/USERNAME/$USERNAME/g -e s/VOLUMENAME/$VOLUMENAME/g -e s/VOLUMEDESCRIPTION/$VOLUMEDESCRIPTION/g -e s/BLOCKSIZE/$BLOCKSIZE/g -e s/GATEWAYTYPE/$GATEWAYTYPE/g -e s/GATEWAYPORT/$GATEWAYPORT/g -e s/HOSTNAME/$HOSTNAME/g >> $OUTPUTFILE
{
   "users": {
      "create": [
         {
             "username": "USERNAME"
         }
      ],
      "delete": []
   },
   "volumes": {
      "create": [
         {
            "name": "VOLUMENAME",
            "description": "VOLUMEDESCRIPTION",
            "blocksize": BLOCKSIZE,
            "owner": "USERNAME",
            "private": "true",
            "archive": "false"
         }
      ],
      "delete": []
   },
   "gateways": {
      "create": [
         {
            "owner": "USERNAME",
            "volume": "VOLUMENAME",
            "type": "GATEWAYTYPE",
            "host": "HOSTNAME",
            "port": GATEWAYPORT,
            "driver": "syndicate.rg.drivers.disk"
         }
      ],
      "delete": []
   }
}
EOF
