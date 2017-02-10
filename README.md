# Syndicate Tests

This repo contains tests and a test running framework for Syndicate.  It can be
run standalone or through a Jenkins CI.  Test success/failure is reported using
the [Test Anything Protocol](http://testanything.org/)(TAP).

Syndicate's environment is configured in `config.sh`. 

The tests are run with `testrunner.py`, which reads YAML files (syntax below),
runs the tests and generates output.  _This requires that `pyyaml` be
installed.  Usually available as `python-yaml` or similar from your friendly
package manager._

There's a convenience script, `testwrapper.sh` that will run tests
matching `tests/*.yml`, it puts their TAP output in `results` and the output of
the commands in `output`

The `testwrapper.sh` script can also run individual tests and can execute the
testrunner.py script in the python debugger.  The testwrapper.sh syntax is as
follows:

### testwrapper.sh command

```
usage: testwrapper.sh [-d] [-i] [-v] [-n <test number>]

   -d     Debug testrunner.py

   -i     Interactively run testwrapper.sh, asks (y/n) whether to run each test

   -n     number
            The test number specified
            Either "-n 1" or "-n 001" would run the "001_setup.yml" test

   -v     verbose, run with DEBUG logging
```

### testrunner.py command

```
$ python testrunner.py -h
usage: testrunner.py [-h] [-d] [-i] [-t TAP_FILE] [-f TIME_FORMAT]
                     tasks_file output_file

positional arguments:
  tasks_file            YAML tasks input filename
  output_file           muxed output/error filename

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           print debugging info
  -i, --immediate       immediately print subprocess stdout/err
  -t TAP_FILE, --tap_file TAP_FILE
                        TAP output filename
  -f TIME_FORMAT, --time_format TIME_FORMAT
                        specify a strftime() format
```
## Adding tests

Add tests to the `tests` folder, named in the format `###_description.yml`,
using the test syntax specified below.

## Tests file syntax

The syntax of the testing files has two block types, `setup` and `tasks`.

### Setup Blocks

```
- name: setup_block
  type: setup
  tmpdirs:
    - name: myconfig
      varname: config
  randnames:
    - myvar
    - thatvar
  vars:
    - name: config_dir
      value: "$config/"
  randloop:
    - name: rand_ex
      quantity: 4
    - name: copy_ex
      copy: rand_ex
      prepend: /
  seqloop:
    - name: seq_ex
      quantity: 5
      step: 1
      start: 14
  valueloop:
    - name: val_ex
      values:
        - larry
        - moe
        - curly
    - name: val_dictionary
      values:
        - start: 0
          stop: 4096
        - start: 0
          stop: 8192
  debug: verbose stdout stderr
  comment: comments are printed when verbose (or "-v") is enabled 
```

Setup is used to define variables, set debug options, create testing directories, and create files with random contents.

#### Variables

There are two types of variables, scalars and arrays.  Scalars can be used in a
variety of contexts, arrays can only be used with the `loop_on` construct for
task blocks.

Scalars are accessed using `$var_name` or `${var_name}` - the latter is
required if you have a word character immediately next to the variable.

*Scalars:*

* `tmpdirs` - Creates temporary directories prefixed with `name`, and assigned to variable `varname`, in the system `/tmp` directory.

* `randnames` - From the `name` given, assign a value `name-<random characters>`.

* `vars` - Assign `name` a value `value`.  `value` can include other variables.

*Arrays:*

* `randloop` - loop version of `randnames` - generate `quantity` random names in an array. It is also possible to copy a _randloop_ using the `copy` option.  This is useful in conjunction with `prepend`, which allows you to prepend a path to each element of an existing _randloop_.

* `seqloop` - generate `quantity` numbers, with a selectable `start` (default is `0`) and `step` (default is `1`) size.

* `valueloop` - use the `values` list supplied as an array or array (list) of dictionaries.  Declare the name of the valueloop with _"name:"_

Note that while `setup` value assignments can be used immediately, they always
are evaluated in groups in the order shown above within a setup block.  For
example, running `tmpdirs` then using the variable defined there in `vars` will
work, but the opposite won't.  If you need to get around this, make multiple
setup blocks.


#### Special Variables

There are some special variables that are set:

Global scope:

 - `$tasksf_dir` - directory that the tasks file is located in
 - `$tasksf_name` - filename (basename) of the tasks file.

Within a `loop_on` task:

 - `$<loop name>` - in addition to identifying the loop name, it can be thought of as the array name, making this interchangeable with `$loop_var`.  For example, if the valueloop is named "_val\_ex_", using `$val_ex` within the task will return the current value of the array, and so will `$loop_var`.  The following syntaxes are all acceptable, `$<loop_name>[<index>]` or `${<loop_name>[<index>]}` and even `@<loop_name>`.  While the first two syntaxes return a single value based on the index provided, the `@` symbol will list the entire array as a string (but not for dictionaries).
 - `$loop_var` - the current value of the array being looped on.  Interchangeable with `$<loop_name>` syntax.
 - `$loop_index` - the current index (starts with 0) of the array being looped on. i.e. `$<loop_name>[$loop_index]` is acceptable but works the same as `$<loop_name>` if within a `loop_on` task.

Within a task:

 - `$task_name` - name of the current task

### Task blocks

```
- name: seqblock
  type: sequential
  tasks:
    - name: exits_one
      command: failing command
      exit: 1
      saveout: $config/exit_one
      saveerr: $config/exit_one
    - name: check_output
      command: ./delay.sh bat
      checkout: ${tasksf_dir}/baz.out
      checkerr: ${tasksf_dir}/baz.err

- name: parloopblock
  type: parallel
  loop_on: val_ex
  tasks:
   - name: echo_names
     command: echo $loop_var

- name: backgroundloopblock
  type: background
  loop_on: val_ex
  tasks:
   - name: echo_names
     loop_on: inner_val_ex
     command: echo outerloop = $val_ex, innerloop = $inner_val_ex
     
   - name: execute another command
   - command: echo yet another command
```

Task blocks are used to run commands come in 4 types, `sequential`, `parallel`, `background`,
and `daemon`.

Task blocks are executed in the sequence they appear in the task file.

* `sequential` tasks are run in order within a task block. Each task will be
executed after the previous task has terminated.  The task block will complete
after the last task has completed

* `parallel` tasks are started in parallel, and the task block is completed
after every task within it has exited.

* `background` almost identical to _parallel_, but each task/command in the block must complete before iterating to the next value in the loop.  As you can see from the example, it is possible to have nested loops.  In the case of a _background_ block, the nested/inner loop and the second task all run in parallel but the outer loop will not iterate until all tasks are complete. 

* `daemon` tasks are started in parallel, but are left running while subsequent
task blocks are run. If the daemon process is still running after all other
task blocks have completed, the tasks within are are terminated with `SIGTERM`.

#### Looping

`loop_on` can be included in a task block to cause multiple copies of the same
command to be run, when provided an array of values to loop over.

There are certain variables set each time the loop is run, `$<valueloop name>`,
`$loop_var` and `$loop_index`, which correspondingly have a value from the
array and the current loop number (starting at 0).

If the valueloop array consists of dictionaries, the values corresponding to
the dictionary keys can be addressed using either the dot or subscript format.
For example, `$val_dictionary.start` or `$val_dictionary['start']` identifies
the dictionary values corresponding to the "start" keys described in the "setup
blocks" example above.


### Task Definitions

Each task requires a `name` and one of `command` or `shell` to be defined in
it.  Everything else is optional.

`command` - specifies the command to run. Variables can be interpolated here,
but as this is not run in a sub-shell, piping or redirection is not supported -
see `saveout` and `saveerr` below.

`shell` - works like command, but runs in a subshell. This was added mainly for
fileglobbing abilities and should be used sparingly and only when absolutely
needed.

`infile` - give a filename which will be supplied to `stdin` of the command.

`saveout` and `saveerr` - not tests, but these save the `stdout` and `stderr`
streams to a file.

#### Command Tests

These arguments perform the pass/fail test functionality.

`exit` - The exit code that the command should exit with, if it's not the
default of `0`.  Fail test if the command's exit code is not this value, or if
`exit` isn't specified, if the exit code isn't `0`.

`checkout` and `checkerr` - compare the `stdout` and `stderr` streams to the
contents of a file. Fail test if it contents don't match.  This is the
recommended way, as it compares the entire output, handling things like EOL
characters and binary data.

`compareout` and `compareerr` - compare the `stdout` and `stderr` streams to
the a string, after running `rstrip()` on the stream to remove EOL characters.
Fail test if they don't match. Use this only for commands that output a single
line of text.

`containsout` - Similar to "checkout" except to determine if the `stdout`
stream can be found within a file.

`containserr` - Same as "containsout" except to determine if the `stderr`
stream can be found within a file.

`rangecheckout` - Again similar to "checkout", except stdout is compared to a specific portion of a file.  The portion is specified with an offset or start point (bytes) and length (bytes).


######NOTE
_checkout_, _checkerr_, _containsout_, _containserr_, and _rangecheckout_ are all compatible with single line or yaml list formats.  For example, the following are both valid options:

```
  containsout: 'look for this text in stdout'
```
or

```
  containsout:
    - 'look for this text'
    - 'or look for this'
    - 'or even this'
```

##Debugging

The test running framework for syndicate includes many debugging capabilities that may be helpful when things aren't quite working right.

#####Logging/Verbosity Options:

Within any block or task of your yaml test file, you can optionally include a "debug:" section.  The following options are available:

```
  show: do not execute commands, just show them
  stderr: print contents of STDERR to screen
  stdout: print contents of STDOUT to screen
  verbose = enable verbose debug output (same as "-v" on the command line)
  off: do nothing
```
The options described above are typically useful in the *__setup__* block whereas the options below are useful in the task sections.

#####Debugging Options:

```
  break : break in testrunner.py when this line is being processed
  gdb: run the task command in gdb
  ddd: run the task command in ddd
  valgrind: run the command with valgrind
```

###Examples:

The example below will print debug logs, stdout, and stderr to the terminal.

```debug: verbose stdout stderr```

You can also add 'show' which will only _show_ the commands that would be executed (without executing them).

```debug: verbose show```

#####Python debugger

Adding 'debug: break' to your test file will cause testrunner.py to break in the python debugger (via your terminal) in the section being executed and prior to running the command.  Also remember that 'testwrapper.sh -d -n \<test number\>' will utilize the python debugger as well.

```
- name: break in python debugger prior to running this command
  type: sequential
  tasks:
    - name: run a simple command
      debug: break
      command: echo test command
```
#####gdb/ddd
You can also run the specified command in a debugger (i.e. _gdb_ or _ddd_)

```
- name: break in gdb
  type: sequential
  tasks:
    - name: run a tool that was compiled with debug symbols
      debug: gdb break main   #break at 'main'
      command: /usr/local/bin/exampletool -c examplearg
```
and you can also add multiple breaks or debugger commands...

```
- name: break in ddd
  type: sequential
  tasks:
    - name: run a tool that was compiled with debug symbols
      debug: 
        - ddd
        - break main   #break at 'main' and the breakpoints specified below...
        - break exampletool.c:32
        - break otherexamplesourcefile.c:128
        - break exampletool.c:512 if strcmp(path, "/example") == 0 #break only if this is true
      command: /usr/local/bin/exampletool -c examplearg
```

Note: For the above example, since the debugger chosen was _ddd_, if you are running your testing environment in docker, you would need to start "sshd" then ssh to the container in order to run with X11 and see the GUI.

#####Valgrind

You can run any task command with valgrind symply by adding `debug: valgrind` to the task block.  This will run valgrind using the following valgrind default options, `--tool=memcheck --leak-check=yes --num-callers=20 --track-fds=yes`

```
- name: run valgrind with default options
  type: sequential
  tasks:
    - name: run a tool with valgrind
      debug: valgrind
      command: /usr/local/bin/exampletool -c examplearg
```

If you add arguments to "valgrind", the testrunner knows to no longer use the default valgrind options, as shown below.

```
- name: run valgrind with your own options
  type: sequential
  tasks:
    - name: run a tool with valgrind and your own valgrind options
      debug: valgrind --tool=memcheck --tool=helgrind
      command: /usr/local/bin/exampletool -c examplearg
```

If you don't want to write out all of the valgrind arguments, you can also specify valgrind tools (without specifying "valgrind").  The testrunner will automatically fill in the proper valgrind syntax.  Currently, the testrunner knows about the tools shown in the example below.

```
- name: run valgrind by simply specifying a valgrind tool
  type: sequential
  tasks:
    - name: run a tool with a valgrind tool
      debug: callgrind helgrind memcheck leakcheck
      command: /usr/local/bin/exampletool -c examplearg
```
Lastly, if you plan to use callgrind, you should also consider installing kcachegrind.