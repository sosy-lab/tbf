# Input-using Verifier (IUV)

To run IUV, run
`./run_iuv -i TEST_GENERATOR [--execution|--validators cpachecker --witness_validators] FILE`
from the repository's root directory,
where `TEST_GENERATOR` is one of `{crest, cpatiger, klee, random}`.

[CREST](http://jburnim.github.io/crest/) is a concolic tester.
[CPATiger](http://forsyte.at/software/cpatiger/) is a multi-goal tester based on the model checker CPAchecker.
[KLEE](klee.github.io) is a symbolic execution-based tester and verifier.
Random is a very simple implementation of a random tester.
