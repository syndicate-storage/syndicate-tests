#!/usr/bin/env bash
# Configuration for Syndicate Tests

export SYNDICATE_ADMIN="syndicate-ms@example.com"

export SYNDICATE_MS="http://ms:8080"
export SYNDICATE_MS_ROOT=/opt/ms
export SYNDICATE_MS_KEYDIR=${SYNDICATE_MS_ROOT}
export SYNDICATE_PRIVKEY_PATH=${SYNDICATE_MS_KEYDIR}/admin.pem

export SYNDICATE_ROOT=${SYNDICATE_ROOT:-/usr/bin}
export SYNDICATE_TOOL=${SYNDICATE_ROOT}/syndicate
export SYNDICATE_RG_ROOT=${SYNDICATE_ROOT}
export SYNDICATE_UG_ROOT=${SYNDICATE_ROOT}
export SYNDICATE_AG_ROOT=${SYNDICATE_ROOT}

export SYNDICATE_PYTHON_ROOT=/usr/lib/python2.7/dist-packages/

export USE_VALGRIND=${USE_VALGRIND:-0}

