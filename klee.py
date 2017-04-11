from utils import execute
import utils
import glob
import os
import logging

include_dir = './klee/include/'
lib_dir = './klee/lib'
bin_dir = './klee/bin'
tests_dir = './klee-last'

error_return = 117


class InputGenerator(utils.InputGenerator):

    def __init__(self, timelimit=0, search_heuristic=['random-path', 'nurs:covnew']):
        self.timelimit = int(timelimit) if timelimit else 0
        if type(search_heuristic) is not list:
            self.search_heuristic = list(search_heuristic)
        else:
            self.search_heuristic = search_heuristic

        self._run_env = os.environ.copy()
        self._run_env['PATH'] = bin_dir + os.pathsep + self._run_env['PATH']
        self._run_env['LD_LIBRARY_PATH'] = lib_dir + os.pathsep + self._run_env['LD_LIBRARY_PATH']

    @staticmethod
    def get_name():
        return 'klee'

    def get_run_env(self):
        return self._run_env

    def _get_sym_stmt(self, varname):
        statement = ["klee_make_symbolic(&", varname, ", sizeof(", varname, "), \"", varname, "\")"]
        return "".join(statement)

    def replace_with_assume(self, assumption):
        c_assumption = assumption
        if c_assumption == False:
            c_assumption = "1==0"
        elif c_assumption == True:
            c_assumption = "1==1"
        return "klee_assume(" + c_assumption + ")"

    def _create_input_generation_cmds(self, filename):
        compiled_file = '.'.join(os.path.basename(filename).split('.')[:-1] + ['bc'])
        compile_cmd = ['clang', '-I', include_dir, '-emit-llvm', '-c', '-g', '-o', compiled_file, filename]
        input_generation_cmd = ['klee']
        if self.timelimit > 0:
            input_generation_cmd += ['-max-time', str(self.timelimit)]
        input_generation_cmd += ['-search=' + h for h in self.search_heuristic]
        input_generation_cmd += [compiled_file]

        return [compile_cmd, input_generation_cmd]

    @staticmethod
    def _create_compile_harness_cmd(filename):
        compiled_file = '.'.join(os.path.basename(filename).split('.')[:-1] + ['o'])
        cmd = ['gcc', '-L', lib_dir, filename, '-l', 'kleeRuntest', '-o', compiled_file]
        return cmd, compiled_file

    def check_inputs(self, filename):
        compile_cmd, output_file = self._create_compile_harness_cmd(filename)
        execute(compile_cmd, env=self.get_run_env())

        if not os.path.exists(tests_dir):
            raise FileNotFoundError("Directory " + tests_dir + " should have been created, but doesn't exist.")

        for test_case in glob.iglob(tests_dir + '/*.ktest'):
            test_cmd = ['./' + output_file]
            test_env = self.get_run_env().copy()
            test_env['KTEST_FILE'] = test_case
            result = execute(test_cmd, env=test_env)

            if self.error_reached(result):
                return True
        return False

    def analyze(self, filename):
        self.generate_input(filename)
        return self.check_inputs(filename)