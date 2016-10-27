#!/usr/bin/env python
# testrunner.py
# loads a yaml file, runs tests defined within that file

import argparse
import collections
import datetime
import itertools
import logging
import os
import pprint
import random
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
import yaml

# logging
log_level = logging.ERROR

logging.basicConfig(level=log_level,
                    format='%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s',
                    datefmt="%Y-%m-%dT%H:%M:%S")

logging.Formatter.converter = time.gmtime

logger = logging.getLogger()

# globals
global args
global r_vars  # dict of replacement vars
global loop_vars  # dict of arrays of vars to loop tasks on

def parse_args():

    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('tasks_file',
                        type=argparse.FileType('r'),
                        help="YAML tasks input filename")

    parser.add_argument('output_file',
                        type=argparse.FileType('w'),
                        help="muxed output/error filename")

    parser.add_argument('-d', '--debug',
                        action="store_true",
                        help="print debugging info")

    parser.add_argument('-i', '--immediate',
                        action="store_true",
                        help="immediately print subprocess stdout/err")

    parser.add_argument('-t', '--tap_file',
                        help="TAP output filename")

    parser.add_argument('-f', '--time_format',
                        default="%Y-%m-%dT%H:%M:%S.%f",
                        help="specify a strftime() format")

    args = parser.parse_args()


def import_env():

    global r_vars

    r_vars = {}

    env_var_names = [
        "SYNDICATE_ADMIN",
        "SYNDICATE_MS",
        "SYNDICATE_MS_ROOT",
        "SYNDICATE_MS_KEYDIR",
        "SYNDICATE_PRIVKEY_PATH",
        "SYNDICATE_ROOT",
        "SYNDICATE_TOOL",
        "SYNDICATE_RG_ROOT",
        "SYNDICATE_UG_ROOT",
        "SYNDICATE_AG_ROOT",
        "SYNDICATE_PYTHON_ROOT",
    ]

    logger.debug("Environmental Vars:")

    for e_key in env_var_names:
        r_vars[e_key] = os.environ[e_key]
        logger.debug(" %s=%s" % (e_key, r_vars[e_key]))


def tmpdir(name, varname=None, mode=0700):

    global r_vars

    testprefix = "synd-" + name + "-"
    testdir = tempfile.mkdtemp(dir="/tmp", prefix=testprefix)

    os.chmod(testdir, mode)

    if varname is None:
        varname = name
    r_vars[varname] = testdir

    logger.debug("Created tmpdir '%s', with path: '%s', with mode: '%o'" % (varname, testdir, mode))


def randstring(size):
    pattern = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return "".join([random.choice(pattern) for _ in range(size)])


def randname(name, size=12, varname=None):

    global r_vars

    r_name = "%s-%s" % (name, randstring(size))

    if varname is None:
        varname = name
    r_vars[varname] = r_name

    logger.debug("Created randname '%s' with value '%s'" %
                 (varname, r_name))


def randloop(name, quantity, size=12, varname=None):

    global loop_vars

    vararray = []

    for i in xrange(0, quantity):
        vararray.append("%s-%s" % (name, randstring(size)))

    if varname is None:
        varname = name

    loop_vars[varname] = vararray

    logger.debug("Created random loop_var '%s' with %d items" %
                 (varname, quantity))


def seqloop(name, quantity, start=0, step=1, varname=None):

    global loop_vars

    if varname is None:
        varname = name

    loop_vars[varname] = range(start, start + quantity * step, step)

    logger.debug("Created sequential loop_var '%s' with %d items" %
                 (varname, quantity))


def valueloop(name, values, varname=None):

    global loop_vars

    if varname is None:
        varname = name

    loop_vars[varname] = values

    logger.debug("Created values loop_var '%s' with %d items" %
                 (varname, len(loop_vars[varname])))


def newvar(name, value):

    global r_vars

    r_vars[name] = replace_vars(value)

    logger.debug("Created newvar '%s' with value '%s'" % (name, r_vars[name]))


def replace_vars(string):

    global r_vars

    # convert subscript format to dot format, for dictionaries
    string = re.sub(r"\[\'", ".", string)
    string = re.sub(r"\'\]", "", string)

    # first capture with explicit {}'s
    rcv = re.compile('\$\{(\w+\.\w+|\w+)\}(?:\W|$)*?')
    rcv_matches = rcv.findall(string)

    for match in rcv_matches:
        if match in r_vars:
            rr = re.compile('\$\{%s\}' % match)
            string = rr.sub(r_vars[match], string, count=1)
        else:
            logger.error("Unknown variable: '$%s' in '%s'" %
                         (match, string))

    # second capture on space/word boundaries with and without dictionary keys
    rsv = re.compile('\$(\w+\.\w+|\w+)(?:\W|$)*?')
    rsv_matches = rsv.findall(string)

    for match in rsv_matches:
        if match in r_vars:
            rr = re.compile('\$%s' % match)
            string = rr.sub(r_vars[match], string, count=1)
        else:
            logger.error("Unknown variable: '$%s' in '%s'" %
                         (match, string))

    return string


class CommandRunner():
    """
    Encapsulates running a subprocess and validates return code
    and optionally stdout/err streams
    """

    def __init__(self, cmd_desc, taskb_name):

        self.c = {}
        self.p = None
        self.run_in_shell = False
        self.out_th = {}
        self.err_th = {}
        self.start_t = None
        self.end_t = None

        self.taskb_name = taskb_name
        self.q = collections.deque()

        self.c = cmd_desc

        if "shell" in cmd_desc:
            self.run_in_shell = True
            self.c['command'] = cmd_desc['shell']

        for req_key in ["name", "command", ]:
            if req_key not in self.c:
                logger.error("no key '%s' in command description: %s" %
                             (req_key, self.c))
                sys.exit(1)

    def __pipe_reader(self, stream, stream_name, task_desc):

        global args

        for line in iter(stream.readline, b''):
            event = {"time": time.time(), "stream": stream_name,
                     "task": task_desc, "line": line}
            self.q.append(event)

            # print is not thread safe, but works, mostly...
            if args.immediate:
                print self.decorate_output(event)

        stream.close()

        self.end_t = time.time()

    @staticmethod
    def decorate_output(event):

        global args

        event_dt = datetime.datetime.utcfromtimestamp(event['time'])

        return ('%s | %s,%s | %s' % (event_dt.strftime(args.time_format),
                event['task'], event['stream'],
                event['line'].rstrip()))

    def run(self):

        global r_vars

        # $task_name is name of current task
        r_vars['task_name'] = self.c['name']

        # replace variables
        command = replace_vars(self.c['command'])
        self.c['repl_command'] = command

        ON_POSIX = 'posix' in sys.builtin_module_names

        run_params = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
                      "bufsize": 1, "close_fds": ON_POSIX, }

        if "infile" in self.c:
            in_fname = replace_vars(self.c['infile'])
            if os.path.isfile(in_fname):
                run_params["stdin"] = open(in_fname, 'r')
            else:
                logger.error("infile '%s' is not a file" % in_fname)
                sys.exit(1)

        if self.run_in_shell:
            # pass command as string if running in a shell
            logger.debug("Running Task '%s': `%s` in shell" %
                         (self.c['name'], command))
            run_params['shell'] = True
            self.p = subprocess.Popen(command, **run_params)
        else:
            # split command into array for running directly
            logger.debug("Running Task '%s': `%s`" % (self.c['name'], command))
            c_array = shlex.split(command)
            self.p = subprocess.Popen(c_array, **run_params)

        self.start_t = time.time()

        self.out_th = threading.Thread(
                        target=self.__pipe_reader,
                        args=(self.p.stdout, "o",
                              "%s:%s" % (self.taskb_name, self.c['name'])))

        self.out_th.daemon = True  # thread ends when subprocess does
        self.out_th.start()

        self.err_th = threading.Thread(
                        target=self.__pipe_reader,
                        args=(self.p.stderr, "e",
                              "%s:%s" % (self.taskb_name, self.c['name'])))

        self.err_th.daemon = True
        self.err_th.start()

    def terminate(self):

        # check to see if already exited, send terminate signal otherwise
        retcode = self.p.poll()

        if retcode is not None:
            logger.debug("Task '%s' already terminated, exited %d" %
                         (self.c['name'], retcode))
        else:
            logger.debug("Terminating task '%s'" % self.c['name'])
            self.p.terminate()

            # exit likely negative of signal, only set if not set
            if 'exit' not in self.c:
                self.c['exit'] = - signal.SIGTERM

    def send_signal(self, signal):

        logger.debug("Sending signal '%d' to task '%s'" %
                     (signal, self.c['name']))

        self.p.send_signal(signal)

        # exit is likely negative of signal, only set if not set
        if 'exit' not in self.c:
            self.c['exit'] = - signal

    def duration(self, multiplier=1):

        # multiplier is to easily generate mili/micro-seconds
        if self.end_t is not None:
            return (self.end_t - self.start_t) * multiplier
        else:
            return None

    def finish(self, tap_writer):

        failures = []

        self.out_th.join()
        self.err_th.join()
        self.p.wait()

        logger.debug("Duration of task '%s': %.6f" %
                     (self.c['name'], self.duration()))

        # $task_name is name of current task
        r_vars['task_name'] = self.c['name']

        # default is 0, check against this in any case
        exit = 0

        if 'exit' in self.c:
            exit = self.c['exit']

        if self.p.returncode == exit:
            logger.debug("Task '%s' exited correctly: %s" %
                         (self.c['name'], self.p.returncode))
        else:
            exit_fail = ("Task '%s' incorrect exit: %s, expecting %s" %
                         (self.c['name'], self.p.returncode, exit))
            logger.error(exit_fail)
            failures.append(exit_fail)

        stdout_str = ""
        stderr_str = ""

        for dq_item in self.q:
            if dq_item['stream'] == "o":
                stdout_str += dq_item['line']
            elif dq_item['stream'] == "e":
                stderr_str += dq_item['line']
            else:
                raise Exception("Unknown stream: %s" % dq_item['stream'])

        # saving stdout/stderr is optional
        if 'saveout' in self.c:
            so_fname = replace_vars(self.c['saveout'])

            parentdir = os.path.dirname(so_fname)
            if not os.path.isdir(parentdir):
                logger.error("Parent '%s' is not a directory for saveout file '%s'" %
                             (parentdir, so_fname))
                sys.exit(1)

            so_f = open(so_fname, 'w')
            so_f.write(stdout_str)
            so_f.close()

            logger.debug("Saved stdout of task '%s' to '%s'" %
                         (self.c['name'], so_fname))

        if 'saveerr' in self.c:
            se_fname = replace_vars(self.c['saveerr'])

            parentdir = os.path.dirname(se_fname)
            if not os.path.isdir(parentdir):
                logger.error("Parent '%s' is not a directory for saveerr file '%s'" %
                             (parentdir, se_fname))
                sys.exit(1)

            se_f = open(se_fname, 'w')
            se_f.write(stdout_str)
            se_f.close()

            logger.debug("Saved stderr of task '%s' to '%s'" %
                         (self.c['name'], se_fname))

        # checks against stdout/stderr are optional
        if 'checkout' in self.c:
            checkout_fname = replace_vars(self.c['checkout'])
            if not os.path.isfile(checkout_fname):
                logger.error("Task '%s', nonexistant checkout file '%s'" %
                             (self.c['name'], checkout_fname))
                sys.exit(1)

            if stdout_str == open(checkout_fname).read():
                logger.debug("Task '%s' stdout matches contents of '%s'" %
                             (self.c['name'], checkout_fname))
            else:
                checkout_fail = ("Task '%s' stdout does not match contents of '%s'" %
                                 (self.c['name'], checkout_fname))
                logger.error(checkout_fail)
                failures.append(checkout_fail)

        if 'checkerr' in self.c:
            checkerr_fname = replace_vars(self.c['checkerr'])
            if not os.path.isfile(checkerr_fname):
                logger.error("Task '%s', nonexistant checkerr file '%s'" %
                             (self.c['name'], checkerr_fname))
                sys.exit(1)

            if stderr_str == open(checkerr_fname).read():
                logger.debug("Task '%s' stderr matches contents of '%s'" %
                             (self.c['name'], checkerr_fname))
            else:
                checkerr_fail = ("Task '%s' stderr does not match contents of '%s'" %
                                 (self.c['name'], checkerr_fname))
                logger.error(checkerr_fail)
                failures.append(checkerr_fail)

        if 'partialcheckout' in self.c:
            partialcheckout_fname = replace_vars(self.c['partialcheckout'])
            if not os.path.isfile(partialcheckout_fname):
                logger.error("Task '%s', nonexistant partialcheckout file '%s'" %
                             (self.c['name'], partialcheckout_fname))
                sys.exit(1)

            if stdout_str in open(partialcheckout_fname).read():
                logger.debug("Task '%s' stdout matches contents within '%s'" %
                             (self.c['name'], partialcheckout_fname))
            else:
                partialcheckout_fail = ("Task '%s' stdout does not match contents of '%s'" %
                                 (self.c['name'], partialcheckout_fname))
                logger.error(partialcheckout_fail)
                failures.append(partialcheckout_fail)

        # check out/err against strings, after rstrip of output
        if 'compareout' in self.c:
            cout_rv = replace_vars(str(self.c['compareout']))
            if cout_rv == stdout_str.rstrip():
                logger.debug("Task '%s' stdout matches string of '%s'" %
                             (self.c['name'], cout_rv))

            else:
                cout_fail = ("Task '%s' stdout '%s' does not match string '%s'" %
                             (self.c['name'], stdout_str.rstrip(), cout_rv))
                logger.error(cout_fail)
                failures.append(cout_fail)

        if 'compareerr' in self.c:
            cerr_rv = replace_vars(str(self.c['compareerr']))
            if cerr_rv == stderr_str.rstrip():
                logger.debug("Task '%s' stderr matches string of '%s'" %
                             (self.c['name'], cerr_rv))

            else:
                cerr_fail = ("Task '%s' stderr '%s' does not match string '%s'" %
                             (self.c['name'], stderr_str.rstrip(), cerr_rv))
                logger.error(cerr_fail)
                failures.append(cerr_fail)

        if tap_writer:

            yaml_data = {"duration_ms": "%.6f" % self.duration(1000),
                         "command": self.c['repl_command']}
            testname = "%s : %s" % (self.taskb_name, self.c['name'])

            if failures:
                yaml_data["failures"] = failures
                tap_writer.record_test(False, testname, yaml_data)
            else:
                tap_writer.record_test(True, testname, yaml_data)

        return {"failures": failures, "q": self.q}


class RunParallel():

    def __init__(self, taskblock, tap_writer=None):

        global loop_vars

        self.runners = []
        self.run_out = []
        self.tasks = []

        if 'tasks' not in taskblock:
            logger.error("No tasks in taskblock '%s'" % taskblock['name'])
            sys.exit(1)

        if 'loop_on' in taskblock:
            if taskblock['loop_on'] in loop_vars:
                self.tasks = self.loop_tasks(taskblock['loop_on'], taskblock)
            else:
                logger.error("loop_on array '%s' is unknown in taskblock '%s'" %
                             (taskblock['loop_on'], taskblock['name']))
                sys.exit(1)
        else:
            self.tasks = taskblock['tasks']

        self.taskblock_name = taskblock['name']
        self.tap_writer = tap_writer

    def loop_tasks(self, varname, taskblock):

        global loop_vars
        global r_vars

        tasks = []

        for index, loop_var in enumerate(loop_vars[varname]):
             for task in taskblock['tasks']:
                if type(loop_var) is dict:                          #check if the first element in the loop_var list is a dictionary
                    for key in loop_var.keys():                     #if dict, for each key in the dictionary
                         varkeystr = "%s.%s" % (varname,key)        #create a r_vars key based on the loop "varname" and dict key using the dot format
                         r_vars[varkeystr] = str(loop_var[key])     #set the dict value and the new key in r_vars to be used in replace_vars
                         varkeystr = "loop_var.%s" % (key)          #maintain the original "loop_var" name for backward compatibility, i.e. use "loop_var" instead of the specified loop "varname", use dot format
                         r_vars[varkeystr] = str(loop_var[key])
                else:
                    varkeystr = str(varname)                        #if not a dict, i.e. basic list, does not use the dictionary key as part of the loop "varname" key, does not use dot format
                    r_vars[varkeystr] = str(loop_var)
                    r_vars['loop_var'] = str(loop_var)              #maintain the original "loop_var" name for backward compatibility, i.e. use "loop_var" instead of the specified loop "varname"

                r_vars['loop_index'] = str(index)
                modified_task = task.copy()
                modified_task['command'] = replace_vars(task['command'])

                for key in ['name', 'saveout', 'saveerr', ]:
                    if key in task:
                        modified_task[key] = "%s-%d" % (task[key], index)

                tasks.append(modified_task)

        return tasks

    def num_tests(self):
        return len(self.tasks)

    def run(self):
        for task in self.tasks:
            cr = CommandRunner(task, self.taskblock_name)
            self.runners.append({"name": task['name'], "cr": cr})
            cr.run()

        for runner in self.runners:
            self.run_out.append(runner['cr'].finish(self.tap_writer))


class RunSequential(RunParallel):

    def run(self):
        for task in self.tasks:
            cr = CommandRunner(task, self.taskblock_name)
            cr.run()
            self.run_out.append(cr.finish(self.tap_writer))


class RunDaemon(RunParallel):

    def run(self):
        for task in self.tasks:
            cr = CommandRunner(task, self.taskblock_name)
            self.runners.append({"name": task['name'], "cr": cr})
            cr.run()

    def stop(self):
        for runner in self.runners:
            runner['cr'].terminate()
            self.run_out.append(runner['cr'].finish(self.tap_writer))


class TAPWriter():

    def __init__(self, tap_filename):
        """
        generate a TAP file of results
        """

        self.current_test = 0

        self.tap_file = open(tap_filename, 'w')

    def write_header(self, num_tests):

        self.tap_file.write("TAP version 13\n")
        self.tap_file.write("1..%d\n" % num_tests)

    def record_test(self, success, testname, extra_data=None):

        global args
        global r_vars

        self.current_test += 1

        # add tasks file name to description
        testdesc = "%s : %s" % (r_vars['tasksf_name'], testname)

        if success:
            self.tap_file.write("ok %d - %s\n" %
                                (self.current_test, testdesc))
        else:
            self.tap_file.write("not ok %d - %s\n" %
                                (self.current_test, testdesc))

        if extra_data:

            # YAML must be indented:
            # http://testanything.org/tap-version-13-specification.html#yaml-blocks

            yaml_str = yaml.dump(extra_data, indent=4,
                                 explicit_start=True, explicit_end=True,
                                 default_flow_style=False).rstrip()

            indented = '\n'.join(
                "  " + line for line in yaml_str.split('\n')) + '\n'

            self.tap_file.write(indented)

    def __del__(self):
        self.tap_file.close()


class TaskBlocksRunner():

    task_blocks = []
    runners = []
    daemons = []
    runb_out = []
    tap_writer = None

    def __init__(self, tasks_filename, tap_filename=""):
        """
        Load the tests file and parse from YAML
        Verify taskblock syntax
        """

        try:
            self.task_blocks = yaml.safe_load(tasks_filename)
        except yaml.YAMLError as exc:
            logger.error("Problem loading input file: " + exc)
            sys.exit(1)

        if tap_filename:
            tap_writer = TAPWriter(tap_filename)

        num_tests = 0

        for taskb in self.task_blocks:

            # validate task blocks from YAML
            for req_key in ["name", "type", ]:
                if req_key not in taskb:
                    logger.error("No '%s' defined in task block: %s" %
                                 (req_key, taskb))
                    sys.exit(1)

            if taskb['type'] not in ["setup", "daemon", "sequential", "parallel", ]:
                logger.error("Unknown task type '%s' in task block: %s" %
                             (taskb['type'], taskb))
                sys.exit(1)

            # create the task blocks
            if taskb['type'] == "setup":
                self.setup_block(taskb)

            elif taskb['type'] == "daemon":
                daemon_runner = RunDaemon(taskb, tap_writer)
                num_tests += daemon_runner.num_tests()
                self.runners.append(
                    {"name": taskb['name'], "runner": daemon_runner,
                     "type": taskb['type']})

            elif taskb['type'] == "sequential":
                seq_runner = RunSequential(taskb, tap_writer)
                num_tests += seq_runner.num_tests()
                self.runners.append(
                    {"name": taskb['name'], "runner": seq_runner,
                     "type": taskb['type']})

            elif taskb['type'] == "parallel":
                par_runner = RunParallel(taskb, tap_writer)
                num_tests += par_runner.num_tests()
                self.runners.append(
                    {"name": taskb['name'], "runner": par_runner,
                     "type": taskb['type']})

            else:
                logger.error("Unknown task type '%s' in task block: %s" %
                             (taskb['type'], taskb))
                sys.exit(1)

        if tap_writer:
            tap_writer.write_header(num_tests)

    def setup_block(self, setupb):

        if 'tmpdirs' in setupb:
            for tdir in setupb['tmpdirs']:
                if 'mode' in tdir:
                    tmpdir(tdir['name'], tdir['varname'], tdir['mode'])
                else:
                    tmpdir(tdir['name'], tdir['varname'])

        if 'randnames' in setupb:
            for rname in setupb['randnames']:
                randname(rname)

        if 'vars' in setupb:
            for v_name in setupb['vars']:
                newvar(v_name['name'], v_name['value'])

        if 'randloop' in setupb:
            for rloop in setupb['randloop']:
                randloop(rloop['name'], rloop['quantity'])

        if 'seqloop' in setupb:
            for sloop in setupb['seqloop']:

                start = 0
                step = 1

                if sloop['start']:
                    start = sloop['start']
                if sloop['step']:
                    step = sloop['step']

                seqloop(sloop['name'], sloop['quantity'], start, step)

        if 'valueloop' in setupb:
            for vloop in setupb['valueloop']:
                for req_key in ["name", "values", ]:
                    if req_key not in vloop:
                        logger.error("valueloop required key '%s' not found in: %s" %
                                     (req_key, vloop))
                        sys.exit(1)

                if not isinstance(vloop['values'], list):
                    logger.error("non-list values in valueloop: %s" % vloop)
                    sys.exit(1)

                valueloop(vloop['name'], vloop['values'])

    def run_task_blocks(self):

        for runner in self.runners:
            runner['runner'].run()
            if runner['type'] != "daemon":
                self.runb_out.append(runner['runner'].run_out)
            else:
                self.daemons.append(runner)

    def stop_daemons(self):

        for daemon in self.daemons:
            daemon['runner'].stop()
            self.runb_out.append(daemon['runner'].run_out)

    def print_timesorted(self, output_file):

        global args

        all_output = itertools.chain()

        for tasks in self.runb_out:
            for task in tasks:
                all_output = itertools.chain(all_output, task['q'])

        sorted_outs = sorted(all_output, key=lambda k: k['time'])

        for dq_item in sorted_outs:
            output_file.write(CommandRunner.decorate_output(dq_item) + "\n")

if __name__ == "__main__":
    parse_args()
    import_env()

    global args
    global r_vars
    global loop_vars

    loop_vars = {}

    if args.debug:
        logger.setLevel(logging.DEBUG)

    start_t = time.time()
    start_dt = datetime.datetime.utcfromtimestamp(start_t)
    logger.debug("Started at %s" % start_dt.strftime(args.time_format))

    tasks_file_abspath = os.path.abspath(args.tasks_file.name)
    r_vars['tasksf_dir'] = os.path.dirname(tasks_file_abspath)
    r_vars['tasksf_name'] = os.path.basename(tasks_file_abspath)

    logger.debug("Running tasks from file '%s'" % tasks_file_abspath)

    tbr = TaskBlocksRunner(args.tasks_file, args.tap_file)

    tbr.run_task_blocks()
    tbr.stop_daemons()
    tbr.print_timesorted(args.output_file)

    args.output_file.close()

    end_t = time.time()
    duration = end_t - start_t
    end_dt = datetime.datetime.utcfromtimestamp(end_t)

    logger.debug("Ended at %s, duration: %.6f" %
                 (end_dt.strftime(args.time_format), duration))
