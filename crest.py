from utils import execute
import utils
import os
from time import sleep

bin_dir = '../crest/bin'
lib_dir = '../crest/lib'
include_dir = '../crest/include'
test_file = 'tests.crest'

class InputGenerator(utils.InputGenerator):

    def __init__(self, timelimit=0, log_verbose=False):
        self.timelimit = int(timelimit) if timelimit else 0
        self.log_verbose = log_verbose

        self._run_env = os.environ.copy()
        self._run_env['PATH'] = bin_dir + os.pathsep + self._run_env['PATH']

    @staticmethod
    def get_name():
        return 'crest'

    def get_run_env(self):
        return self._run_env

    def _create_input_generation_cmds(self, filename):
        return None

    @staticmethod
    def _create_compile_harness_cmd(filename):
        return None, None

    def check_inputs(self, filename, generator_thread=None):
        if not os.path.exists(test_file):
            raise FileNotFoundError("File " + test_file + " should have been created, but doesn't exist.")

        compile_cmd, output_file = self._create_compile_harness_cmd(filename)
        exec_result = execute(compile_cmd, env=self.get_run_env())

        if exec_result.returncode > 0:
            raise utils.CompileError("Failed compiling "
                                     "the test harness. Check stderr for more information.")
        visited_tests = set()
        while generator_thread and generator_thread.is_alive():
            result = self._m(output_file, visited_tests)
            if result:
                return True
            sleep(0.001)  # Sleep for 1 millisecond

        return self._m(output_file, visited_tests)

