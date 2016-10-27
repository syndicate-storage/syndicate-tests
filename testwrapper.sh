#!/usr/bin/env bash
# Runs syndicate tests in PATHDIR, puts TAP results in TESTDIR
# Syntax:
#   -d 			run with python debugger
#   -i			interactively ask which test to run
#   -n <test number>	run the test number specified

TESTDIR=./tests
RESULTDIR=./results
OUTPUTDIR=./output
BASH=/bin/bash

debug=''
if [[ $@ =~ -d ]]; then
  debug='-m pdb'
fi

testnumber=0
if [[ $@ =~ -n ]]; then
  testnumber=`echo $@ | sed -e 's/^.*-n//g' -e 's/^ *0*//g' | xargs printf "%03d"`
fi

# bring in config
source config.sh

# Start testing
echo "Start Time: `date +'%F %T'`"
start_t=`date +%s`
echo "Working in: '`pwd`'"

# remove old results
rm -f ${RESULTDIR}/*.tap

# run the tests
if [ $testnumber -eq 0 ]; then
  for test in $(ls ${TESTDIR}/*.yml ); do
    testname=${test##*/}
    runtest=1
    if [[ $@ =~ -i ]]; then
      runtest=0
      read -p "Run ${testname}? (y/n): " run
      if [[ $run =~ [Yy] ]]; then
         runtest=1
      fi
    fi
    if [ $runtest == 1 ]; then
      echo "Running test: '${testname}'"
      python $debug ./testrunner.py -d -t ${RESULTDIR}/${testname%.*}.tap ${test} ${OUTPUTDIR}/${testname%.*}.out
    fi
  done
else
  test=`find ${TESTDIR} -name "*${testnumber}_*.yml"`
  testname=${test##*/}
  echo "Running test: '${testname}'"
  python $debug ./testrunner.py -d -t ${RESULTDIR}/${testname%.*}.tap ${test} ${OUTPUTDIR}/${testname%.*}.out
fi

echo "Copying logs..."
cp -r /tmp/synd-* $OUTPUTDIR
# change permissions.
# ${OUTPUTDIR} and ${OUTPUTDIR}/.gitignore are owned by the host account thus shouldn't be modified.
chmod -R a+rwx ${OUTPUTDIR}/*.out
chmod -R a+rwx ${OUTPUTDIR}/synd-*

echo "End Time:   `date +'%F %T'`"
end_t=`date +%s`
echo "Elapsed Time: $((${end_t} - ${start_t}))s"

