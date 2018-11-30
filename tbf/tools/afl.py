import glob
import logging
import os

import tbf.utils as utils
from tbf.harness_generation import HarnessCreator
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

module_dir = os.path.dirname(os.path.realpath(__file__))
bin_dir = os.path.join(module_dir, 'afl/bin')
findings_dir = './findings'
name = 'afl-fuzz'
tests_dir = '.'


class InputGenerator(BaseInputGenerator):

    def create_input_generation_cmds(self, program_file, cli_options):
        instrumented_program = './tested.out'
        compiler = self._get_compiler()
        compile_cmd = [
            os.path.join(bin_dir,
                         compiler), self.machine_model.compile_parameter, '-o',
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
            input_gen_cmd += cli_options
        input_gen_cmd += ['--', instrumented_program]
        return [compile_cmd, input_gen_cmd]

    def _create_testcase_dir(self):
        testcase_dir = './initial_testcases'
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
        if 'AFL_PATH' not in env.keys():
            env['AFL_PATH'] = bin_dir
        if 'AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES' not in env.keys():
            env['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = 'true'
        if 'AFL_SKIP_CPUFREQ' not in env.keys():
            env['AFL_SKIP_CPUFREQ'] = 'true'
        return env

    def prepare(self, filecontent, nondet_methods_used):
        harness_creator = HarnessCreator()
        harness = harness_creator._get_vector_read_method()
        harness += harness_creator._get_nondet_method_definitions(
            nondet_methods_used, None)
        content = filecontent + '\n' + harness.decode()
        return content

    def _get_compiler(self):
        env = self.get_run_env()
        if 'AFL_CC' in env.keys():
            if 'clang' in env['AFL_CC']:
                return 'afl-clang'
            else:
                return 'afl-gcc'
        elif utils.get_executable('clang'):
            return 'afl-clang'
        else:
            logging.info("Compiler 'clang' not found. Using gcc.")
            return 'afl-gcc'


class AflTestConverter(TestConverter):

    def _get_test_name(self, test_file):
        return os.path.basename(test_file)

    def _get_test_cases_in_dir(self, directory=None, exclude=None):
        if directory is None:
            directory = tests_dir
        # 'crashes' and 'hangs' cannot lead to an error as long as we don't abort in __VERIFIER_error()
        interesting_subdirs = (os.path.join(directory, d) for d in ('queue'))
        tcs = list()
        for s in interesting_subdirs:
            abs_dir = os.path.join(findings_dir, s)
            for t in glob.glob(abs_dir + '/id:*'):
                test_name = self._get_test_name(t)
                if test_name not in exclude:
                    tcs.append(self._get_test_case_from_file(t))
        return tcs

    def _get_test_case_from_file(self, test_file):
        test_name = self._get_test_name(test_file)
        with open(test_file, 'rb') as inp:
            content = inp.read()
        utils.TestCase(test_name, test_file, content)

    def get_test_vector(self, test_case, nondet_methods):
        vector = utils.TestVector(test_case.name, test_case.origin)
        for line in test_case.content.split(b'\n'):
            vector.add(line)
        return vector
