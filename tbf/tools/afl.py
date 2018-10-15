from tbf.input_generation import BaseInputGenerator
from tbf.testcase_validation import TestValidator as BaseTestValidator
import os
import tbf.utils as utils
import glob
from tbf.harness_generation import HarnessCreator
import pathlib

module_dir = os.path.dirname(os.path.realpath(__file__))
bin_dir = os.path.join(module_dir, 'afl/bin')
findings_dir = utils.get_file_path('findings', temp_dir=True)
name = 'afl-fuzz'
tests_dir = utils.tmp


class InputGenerator(BaseInputGenerator):

    def create_input_generation_cmds(self, program_file, cli_options):
        instrumented_program = 'tested.out'
        compile_cmd = [
            os.path.join(bin_dir,
                         'afl-gcc'), self.machine_model.compile_parameter, '-o',
            instrumented_program, program_file
        ]

        testcase_dir = self._create_testcase_dir()
        input_gen_cmd = [
            os.path.join(bin_dir, 'afl-fuzz'), '-i', testcase_dir, '-o',
            findings_dir
        ]

        # If cli_options is an empty string and we add it to the command,
        # afl-fuzz will interpret the resulting additional space (' ') as
        # the program name and fail
        if cli_options:
            input_gen_cmd.append(cli_options)
        input_gen_cmd += ['--', instrumented_program]
        return [compile_cmd, input_gen_cmd]

    def _create_testcase_dir(self):
        testcase_dir = utils.get_file_path('initial_testcases', temp_dir=True)
        os.mkdir(testcase_dir)
        initial_testcase = os.path.join(testcase_dir, '0.afl-test')
        with open(initial_testcase, 'w+') as outp:
            outp.write(
                1000 * '0\n')  # FIXME: This is an unreliable first test case
        return testcase_dir

    def get_name(self):
        return name

    def get_run_env(self):
        env = utils.get_env()
        env['AFL_PATH'] = bin_dir
        env['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = 'true'
        env['AFL_SKIP_CPUFREQ'] = 'true'
        return env

    def prepare(self, filecontent, nondet_methods_used):
        harness_creator = HarnessCreator()
        harness = harness_creator._get_vector_read_method()
        harness += harness_creator._get_nondet_method_definitions(
            nondet_methods_used, None)
        content = filecontent + '\n' + harness.decode()
        return content

    def _get_test_name(self, test_file):
        return os.path.basename(test_file)

    def get_test_cases(self, exclude=(), directory=tests_dir):
        # 'crashes' and 'hangs' cannot lead to an error as long as we don't abort in __VERIFIER_error()
        interesting_subdirs = ['queue']
        tcs = list()
        for s in interesting_subdirs:
            abs_dir = os.path.join(findings_dir, s)
            for t in glob.glob(abs_dir + '/id:*'):
                test_name = self._get_test_name(t)
                if test_name not in exclude:
                    with open(t, 'rb') as inp:
                        content = inp.read()
                    tcs.append(utils.TestCase(test_name, t, content))
        return tcs


class AflTestValidator(BaseTestValidator):

    def get_name(self):
        return name

    def get_test_vector(self, test_case):
        vector = utils.TestVector(test_case.name, test_case.origin)
        for line in test_case.content.split(b'\n'):
            vector.add(line)
        return vector
