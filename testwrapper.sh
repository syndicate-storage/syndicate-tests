#!/usr/bin/env bash
# Runs syndicate tests in PATHDIR, puts TAP results in TESTDIR
# Syntax:
#   -c                  callgrind on all tests
#   -d 			run with python debugger
#   -i			interactively ask which test to run
#   -n <test number>	run the test number specified
#   -m                  memcheck / valgrind on all tests
#   -o                  run with operf profiler
#   -v                  enable verbose testrunner debug logs

debug=''
if [[ $@ =~ -d ]]; then
  debug='-m pdb'
fi

verbosedebug=''
if [[ $@ =~ -v ]]; then
  verbosedebug='-d'
fi

testnumber=0
if [[ $@ =~ -n ]]; then
  testnumber=`echo $@ | sed -e 's/^.*-n//g' -e 's/^ *0*//g' | xargs printf "%03d"`
fi

# bring in config (in the same directory as this script)
source "${BASH_SOURCE%/*}/config.sh"

# Start testing
echo "Start Time: `date +'%F %T'`"
start_t=`date +%s`
echo "Working in: '`pwd`'"

# remove old results
rm -f ${RESULTDIR}/*.tap

# run the tests
if [ $testnumber -eq 0 ]; then
  for test in $(ls ${TESTDIR}/*.yml); do
    testname=${test##*/}
    runtest=1
    if [[ $@ =~ -i ]]; then
      runtest=0
      read -p "Run ${testname}? (y/n): " run
      if [[ $run =~ [Yy] ]]; then
         runtest=1
      fi
    fi
    valgrindcmd=''
    valgrindmsg=''
    if [[ $@ =~ -m ]]; then
      valgrindcmd="-m ${OUTPUTDIR}/${testname%.*}.valgrind"
      valgrindmsg=" (Memcheck)"
    fi
    if [ $runtest == 1 ]; then
      if [[ -n `cat $test | grep "debug:.*disable"` ]]; then
        echo "Skipping test: '${testname}' (disabled)"
      else
        echo "Running test: '${testname}'${valgrindmsg}"
        python $debug ${CONFIG_ROOT}/testrunner.py $verbosedebug $valgrindcmd -t ${RESULTDIR}/${testname%.*}.tap ${test} ${OUTPUTDIR}/${testname%.*}.out
        if [[ $@ =~ -c ]]; then
          valgrindcmd="-c ${OUTPUTDIR}/${testname%.*}.callgrind"
          echo "            : '${testname}' (Callgrind)"
          python $debug ${CONFIG_ROOT}/testrunner.py $valgrindcmd -t ${OUTPUTDIR}/${testname%.*}.tmptap ${test} ${OUTPUTDIR}/${testname%.*}.tmpout
          rm ${OUTPUTDIR}/${testname%.*}.tmptap ${OUTPUTDIR}/${testname%.*}.tmpout
        fi
        if [[ $@ =~ -o ]]; then
          operfcmd="-o ${OUTPUTDIR}/${testname%.*}.operf"
          echo "            : '${testname}' (operf)"
          python $debug ${CONFIG_ROOT}/testrunner.py $operfcmd -t ${OUTPUTDIR}/${testname%.*}.tmptap ${test} ${OUTPUTDIR}/${testname%.*}.tmpout
          rm ${OUTPUTDIR}/${testname%.*}.tmptap ${OUTPUTDIR}/${testname%.*}.tmpout
        fi
      fi
    fi
  done
else
  test=`find ${TESTDIR} -name "*${testnumber}_*.yml"`
  testname=${test##*/}
  valgrindcmd=''
  valgrindmsg=''
  if [[ $@ =~ -m ]]; then
    valgrindcmd="-m ${OUTPUTDIR}/${testname%.*}.valgrind"
    valgrindmsg=" (Memcheck)"
  fi
  echo "Running test: '${testname}'${valgrindmsg}"
  python $debug ${CONFIG_ROOT}/testrunner.py $verbosedebug $valgrindcmd -t ${RESULTDIR}/${testname%.*}.tap ${test} ${OUTPUTDIR}/${testname%.*}.out
  if [[ $@ =~ -c ]]; then
    valgrindcmd="-c ${OUTPUTDIR}/${testname%.*}.callgrind"
    echo "            : '${testname}' (Callgrind)"
    python $debug ${CONFIG_ROOT}/testrunner.py $valgrindcmd -t ${OUTPUTDIR}/${testname%.*}.tmptap ${test} ${OUTPUTDIR}/${testname%.*}.tmpout
    rm ${OUTPUTDIR}/${testname%.*}.tmptap ${OUTPUTDIR}/${testname%.*}.tmpout
  fi
  if [[ $@ =~ -o ]]; then
    operfcmd="-o ${OUTPUTDIR}/${testname%.*}.operf"
    echo "            : '${testname}' (operf)"
    python $debug ${CONFIG_ROOT}/testrunner.py $verbosedebug $operfcmd -t ${OUTPUTDIR}/${testname%.*}.tmptap ${test} ${OUTPUTDIR}/${testname%.*}.tmpout
    rm ${OUTPUTDIR}/${testname%.*}.tmptap ${OUTPUTDIR}/${testname%.*}.tmpout
  fi
fi

echo "Copying logs..."
cp -r /tmp/synd-* $OUTPUTDIR
# change permissions.
# ${OUTPUTDIR} and ${OUTPUTDIR}/.gitignore are owned by the host account thus shouldn't be modified.
chmod -R a+rwx ${OUTPUTDIR}/*.out
chmod -R a+rwx ${OUTPUTDIR}/[0-9][0-9][0-9]_*
chmod -R a+rwx ${OUTPUTDIR}/synd-*

echo "End Time:   `date +'%F %T'`"
end_t=`date +%s`
echo "Elapsed Time: $((${end_t} - ${start_t}))s"

