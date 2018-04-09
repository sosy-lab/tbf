# Test-based falsifier (TBF)

TBF is a test-based falsifier for C programs.
It is able to prepare C programs for a handful of prominent
test-case generators, and then uses these test-case generators
to create executable tests that uncover bugs in the programs.

## Requirements

  - Python 3.6 or later

## Running TBF

To run TBF, run
`./run_iuv -i TEST_GENERATOR [--execution|--validators cpachecker --witness-validation] FILE`
from the repository's root directory,
where `TEST_GENERATOR` is one of `{afl, crest, cpatiger, fshell, klee, random}`.

* [AFL-fuzz](http://lcamtuf.coredump.cx/afl/) is a greybox fuzz tester.
* [CREST](http://jburnim.github.io/crest/) is a concolic tester (using dynamic symbolic execution)
* [CPATiger](http://forsyte.at/software/cpatiger/) is a multi-goal tester based on the model checker CPAchecker (an automatic, formal verification tool).
* [FShell](http://forsyte.at/software/fshell/) is the CBMC-based tester.
* [KLEE](klee.github.io) is a symbolic execution-based tester and verifier.
* PRTest (also just called 'random') is a very simple, in-house implementation of a random tester.
