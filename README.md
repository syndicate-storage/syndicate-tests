# Syndicate Tests

This repo contains tests and a test runnign framework for Syndicate.  It can be
run standalone, or through a Jenkins CI.  Test sucess/failure is reported using
the [Test Anything Protocol](http://testanything.org/)(TAP).

Syndicate's environment is configured in `config.sh`. 

The tests are run with `testrunner.py`, which reads YAML files (syntax below),
runs the tests and generates output.  _This requires that `pyyaml` be
installed.  Usually available as `python-yaml` or similar from your friendly
package manager._

There's a convenience script, `testwrapper.sh` that will run all the tests
matching `tests/*.yml`, it puts their TAP output in `results` and the output of
the commands in `output`

The `testwrapper.sh` script can also run individual tests and can execute the
testrunner.py script in the python debugger.  The testwrapper.sh syntax is as
follows:

### testwrapper.sh command

```
usage: testwrapper.sh [-d] [-i] [-n <test number>]

   -d     Debug testrunner.py

   -i     Interactively run testwrapper.sh, asks (y/n) whether to run each test

   -n number
          The test number specified
          Either "-n 1" or "-n 001" would run the "001_setup.yml" test
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
  valueloop:
    - name: val_dictionary
      values:
        - start: 0
          end: 4096
        - start: 0
          end: 8192
```

Setup is used to define variables, create testing directories, and files with
random contents.

#### Variables

There are two types of variables, scalars and arrays.  Scalars can be used in a
variety of contexts, arrays can only be used with the `loop_on` construct for
task blocks.

Scalars are accessed using `$var_name` or `${var_name}` syntax - the latter is
required if you have a word character immediately next to the variable.

*Scalars:*

`tmpdirs` - Creates temporary directories prefixed with `name`, and assigned to
variable `varname`, in the system `/tmp` directory.

`randnames` - From the `name` given, assign a value `name-<random characters>`

`vars` - Assign `name` a value `value`.  `value` can include other variables.

*Arrays:*

`randloop` - loop version of `randnames` - generate `quantity` random names in
an array

`seqloop` - generate `quantity` numbers, with a selectable `start`
(default is `0`) and step (default is `1`) size.

`valueloop` - use the `values` list supplied as an array or array (list) of
dictionaries.  Declare the name of the valueloop with _"name:"_

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

 - `$<loop name>` - in addition to identifying the loop name, it can be thought
   of as the array name, making this interchangeable with `$loop_var`.  For
   example, if the valueloop is named "_val\_ex_", using `$val_ex` within the
   task will return the current value of the array, and so will `$loop_var`
 - `$loop_var` - the current value of the array being looped on.
 - `$loop_index` - the current index (starts with 0) of the array being looped
   on.

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
```

Task blocks are used to run commands come in 3 types, `sequential`, `parallel`,
and `daemon`.

Task blocks are executed in the sequence they appear in the task file.

`sequential` tasks are run in order within a task block. Each task will be
executed after the previous task has terminated.  The task block will complete
after the last task has completed

`parallel` tasks are started in parallel, and the task block is completed
after every task within it has exited.

`daemon` tasks are started in parallel, but are left running while subsequent
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

`partialcheckout` - Same as "checkout" except to determine if the `stdout`
stream can be found within a file.

