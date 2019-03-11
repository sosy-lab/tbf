# TBF

TBF is an automatic test-case generation and execution framework for C programs.
It is able to prepare C programs for a handful of prominent
test-case generators, create a test harness for generated tests
and execute them.

TBF is no longer maintained.
Since [Test-Comp](https://test-comp.sosy-lab.org/) provides a uniform
interface for test-suite generators and an exhaustive comparison,
TBF is no longer necessary.
If you are interested in comparing test-suite generators,
you can use the [archives submitted to Test-Comp](https://test-comp.sosy-lab.org/2019/systems.php)
or take a look at the [competition results](https://test-comp.sosy-lab.org/2019/results/results-verified/).

## Requirements

  - Python 3.5 or later

## Installation

### In virtual environment with pipenv

TBF uses [pipenv](https://docs.pipenv.org/) for easy, local dependency management
during development:

  * If you don't have pipenv installed yet, install it as described
      [on the project's webpage][1].
  * To set up the pipenv for TBF, run from the project's root directory:
    ```
      pipenv install
    ```
  * To run TBF in the dedicated pipenv environment, run `pipenv run bin/tbf`,
    or `pipenv shell` to enter the virtual environment and from there `bin/tbf`.
  

[1]: https://docs.pipenv.org/install/#pragmatic-installation-of-pipenv

### Global/User installation with pip

TBF can be properly installed with `pip`.
For example, to install the current state of tbf for the current user, run
```
  pip install --user .
```

## Usage

Run TBF with parameter `--help` to get an overview over all available command-line parameters.

tbf allows the specification of a test-case generator and a test validation method (e.g., test-case execution).
If both are given, tbf will run the test-case generator and execute the generated test cases in a test harness.
If no test validation method is given, tbf will only run the test-case generator. If you do that, use
parameter `--keep-files` to keep the generated test cases and all other generated files,
or `--write-xml` to keep test-format XMLs describing the generated test cases.

### Examples
#### Falsification with AFL
To run tbf with AFL-fuzz and test-case execution on file `examples/simple.c` from within a `pipenv shell` environment, run:
```bash
  bin/tbf -i afl --execution --stats examples/simple.c
```

Parameter `--stats` makes TBF print statistics on stdout.

After execution, directory `output/` will contain some files of interest, e.g. the test harness as C-file (`harness.c`) and the executable test (`a.out`).

#### Test-case Generation with PRTest
To create a test suite in the XML test-format with tbf and the random tester PRTest [1],
running for 10 seconds and using a 64bit machine model, run:
```bash
  bin/tbf -i random --write-xml --timelimit 10 examples/simple.c
```

After execution, there will be multiple files describing
the test suite in directory `output/test-suite`.
There wil be a metadata file `metadata.xml`,
and one additional XML file for each created test case.

[1]: PRTest is a very simple random-tester included with tbf.

### Supported Test-Case Generators

Currently supported test-case generators are:

  * (`afl`) [AFL-fuzz](http://lcamtuf.coredump.cx/afl/) is a greybox fuzz tester.
  * (`crest`) [CREST](http://jburnim.github.io/crest/) is a concolic tester (using dynamic symbolic execution)
  * (`cpatiger`) [CPATiger](http://forsyte.at/software/cpatiger/) is a multi-goal tester based on the model checker CPAchecker (an automatic, formal verification tool).
  * (`fshell`) [FShell](http://forsyte.at/software/fshell/) is the CBMC-based tester.
  * (`klee`) [KLEE](klee.github.io) is a symbolic execution-based tester and verifier.
  * (`random`) PRTest (also just called 'random') is a very simple, in-house implementation of a random tester.

# Development

To set up the pipenv for development with TBF, run, from the project's root directory: `pipenv install --dev`.

To run pylint and unit tests, run `pipenv run py.test`.

If you copy `contrib/git_hooks/pre-commit-yapf.sh` to file `.git/hooks/pre-commit`,
the python formatter [yapf][2] will automatically run whenever you commit
some code. This assumes that you set up the pipenv environment for TBF development
as specified above.

[2]: https://github.com/google/yapf
