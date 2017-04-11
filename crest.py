import re
import logging
from utils import execute
import utils
import glob
import os

include_dir = '../klee/include/'
lib_dir = '../klee/build/lib'
tests_dir = './klee-last'


class InputGenerator(utils.InputGenerator):

    def __init__(self, timelimit=0, search_heuristic=['random-path', 'nurs:covnew']):
        self.timelimit = int(timelimit) if timelimit else 0
        if type(search_heuristic) is not list:
            self.search_heuristic = list(search_heuristic)
        else:
            self.search_heuristic = search_heuristic

    @staticmethod
    def get_name():
        return 'crest'

    def _get_sym_stmt(self, varname):
        sym_function = ''  # TODO
        statement = ["klee_make_symbolic(&", varname, ", sizeof(", varname, "), \"", varname, "\")"]
        return "".join(statement)

    def replace_with_assume(self, assumption):
        c_assumption = assumption
        if c_assumption == False:
            c_assumption = "1==0"
        elif c_assumption == True:
            c_assumption = "1==1"
        return "klee_assume(" + c_assumption + ")"  # TODO

    def _create_input_generation_cmds(self, filename):
        compiled_file = '.'.join(filename.split('.')[:-1] + ['bc'])
        compile_cmd = ['clang', '-I', include_dir, '-emit-llvm', '-c', '-g', '-o', compiled_file, filename]
        input_generation_cmd = ['klee']
        if self.timelimit > 0:
            input_generation_cmd += ['-max-time', str(self.timelimit)]
        input_generation_cmd += ['-search=' + h for h in self.search_heuristic]
        input_generation_cmd += [compiled_file]

        return [compile_cmd, input_generation_cmd]

    @staticmethod
    def _create_compile_harness_cmd(filename):
        compiled_file = '.'.join(filename.split('.')[:-1] + ['o'])
        cmd = ['gcc', '-L', lib_dir, filename, '-l', 'kleeRuntest', '-o', compiled_file]
        return cmd, compiled_file

    def check_inputs(self, filename):
        compile_cmd, output_file = self._create_compile_harness_cmd(filename)
        execute(compile_cmd)

        for test_case in glob.iglob(tests_dir + '/*.ktest'):
            test_cmd = ['./' + output_file]
            test_env = os.environ.copy()
            test_env['KTEST_FILE'] = test_case
            result = execute(test_cmd, env=test_env)

            if InputGenerator.error_reached(result):
                return True
        return False

    def analyze(self, filename):
        self.generate_input(filename)
        return self.check_inputs(filename)

