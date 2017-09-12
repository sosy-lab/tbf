# Test-based falsifier (TBF)

To run TBF, run
`./run_iuv -i TEST_GENERATOR [--execution|--validators cpachecker --witness_validators] FILE`
from the repository's root directory,
where `TEST_GENERATOR` is one of `{afl, crest, cpatiger, fshell, klee, random}`.


* [AFL-fuzz](http://lcamtuf.coredump.cx/afl/) is a greybox fuzz tester.
* [CREST](http://jburnim.github.io/crest/) is a concolic tester.
* [CPATiger](http://forsyte.at/software/cpatiger/) is a multi-goal tester based on the model checker CPAchecker.
* [FShell](http://forsyte.at/software/fshell/) is CBMC-based FQL tester.
* [KLEE](klee.github.io) is a symbolic execution-based tester and verifier.
* PRTest (also just called 'random') is a very simple implementation of a random tester.
