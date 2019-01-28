import glob
import logging
import os

import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

module_dir = os.path.dirname(os.path.realpath(__file__))
bin_dir = os.path.join(module_dir, 'afl/bin')
FINDINGS_DIR = './findings'
QUEUE_DIR = os.path.join(FINDINGS_DIR, 'queue')
name = 'afl-fuzz'
tests_dir = '.'


class Preprocessor:

    def prepare(self, filecontent, nondet_methods_used, error_method=None):
        content = filecontent
        content += '\n'
        content += utils.EXTERNAL_DECLARATIONS
        content += '\n'
        content += utils.get_assume_method()
        content += '\n'
        content += self._get_vector_read_method()
        if error_method:
            content += utils.get_error_method_definition(error_method)
        for method in nondet_methods_used:
            # append method definition at end of file content
            nondet_method_definition = self._get_nondet_method_definition(method['name'], method['type'],
                                                                          method['params'])
            content += nondet_method_definition
        return content

    @staticmethod
    def _get_vector_read_method():
        return """char * parse_inp(char * __inp_var) {
        unsigned int input_length = strlen(__inp_var)-1;
        /* Remove '\\n' at end of input */
        if (__inp_var[input_length] == '\\n') {
            __inp_var[input_length] = '\\0';
        }

        char * parseEnd;
        char * value_pointer = malloc(16);

        unsigned long long intVal = strtoull(__inp_var, &parseEnd, 0);
        if (*parseEnd != 0) {
          long long sintVal = strtoll(__inp_var, &parseEnd, 0);
          if (*parseEnd != 0) {
            long double floatVal = strtold(__inp_var, &parseEnd);
            if (*parseEnd != 0) {
              fprintf(stderr, "Can't parse input: '%s' (failing at '%s')\\n", __inp_var, parseEnd);
              abort();

            } else {
              memcpy(value_pointer, &floatVal, 16);
            }
          } else {
            memcpy(value_pointer, &sintVal, 8);
          }
        } else {
          memcpy(value_pointer, &intVal, 8);
        }

        return value_pointer;
    }\n\n"""

    @staticmethod
    def _get_nondet_method_definition(method_name, method_type, method_param):
        definition = ""
        definition += utils.get_method_head(method_name, method_type,
                                            method_param)
        definition += ' {\n'
        if method_type != 'void':
            definition += "    unsigned int inp_size = 3000;\n"
            definition += "    char * inp_var = malloc(inp_size);\n"
            definition += "    fgets(inp_var, inp_size, stdin);\n"

            definition += "    return *((" + method_type + "*) parse_inp(inp_var));\n"
        definition += ' }\n'
        return definition


class InputGenerator(BaseInputGenerator):

    def __init__(self, machine_model, log_verbose, additional_options):
        super().__init__(machine_model, log_verbose, additional_options, Preprocessor())

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
            FINDINGS_DIR
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
        interesting_subdirs = (os.path.join(directory, d) for d in [QUEUE_DIR])
        tcs = list()
        for s in interesting_subdirs:
            abs_dir = os.path.abspath(s)
            if not os.path.exists(s):
                continue
            for t in glob.glob(abs_dir + '/id:*'):
                test_name = self._get_test_name(t)
                if test_name not in exclude:
                    tcs.append(self._get_test_case_from_file(t))
        return tcs

    def _get_test_case_from_file(self, test_file):
        test_name = self._get_test_name(test_file)
        with open(test_file, 'rb') as inp:
            content = inp.read()
        return utils.TestCase(test_name, test_file, content)

    def get_test_vector(self, test_case):
        vector = utils.TestVector(test_case.name, test_case.origin)
        for line in test_case.content.split(b'\n'):
            vector.add(line)
        return vector
