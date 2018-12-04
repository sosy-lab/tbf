import glob
import os
import pathlib

import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

name = "prtest"
module_dir = pathlib.Path(__file__).resolve().parent
include_dir = module_dir / "random" / "include"
generator_harness = module_dir / "random" / "random_tester.c"
random_runner = module_dir / "random" / "run.sh"


class Preprocessor:

    def prepare(self, filecontent, nondet_methods_used, error_method=None):
        content = filecontent
        content += '\n'
        content += utils.EXTERNAL_DECLARATIONS
        content += '\n'
        content += utils.get_assume_method()
        content += '\n'
        if error_method:
            content += utils.get_error_method_definition(error_method)
        for method in nondet_methods_used:
            # append method definition at end of file content
            nondet_method_definition = self._get_nondet_method_definition(method['name'], method['type'],
                                                                          method['params'])
            content += nondet_method_definition
        return content

    @staticmethod
    def _get_nondet_method_definition(method_name, method_type, param_types):
        var_name = utils.get_sym_var_name(method_name)
        method_head = utils.get_method_head(method_name, method_type,
                                            param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += [
                '{0} {1};'.format(method_type, var_name),
                'input(&{0}, sizeof({0}), \"{0}\");'.format(var_name),
                'return {0};'.format(var_name)
            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body


class InputGenerator(BaseInputGenerator):

    def __init__(self, machine_model, log_verbose, additional_options):
        super().__init__(machine_model, log_verbose, additional_options, Preprocessor())

    def get_run_env(self):
        return utils.get_env()

    def get_name(self):
        return name

    def create_input_generation_cmds(self, filename, cli_options):
        compiled_file = '.'.join(os.path.basename(filename).split('.')[:-1])
        machinem_arg = self.machine_model.compile_parameter
        compile_cmd = [
            'gcc', '-std=gnu11', machinem_arg, '-I', str(include_dir), '-o',
            compiled_file, str(generator_harness), filename, '-lm'
        ]

        input_generation_cmd = [str(random_runner)]
        if cli_options:
            input_generation_cmd += cli_options
        input_generation_cmd += [compiled_file]

        return [compile_cmd, input_generation_cmd]


class RandomTestConverter(TestConverter):

    @staticmethod
    def _get_test_name(test_file):
        return os.path.basename(test_file)

    def _get_test_case_from_file(self, test_file):
        with open(test_file, 'r') as inp:
            content = inp.read()
        return utils.TestCase(self._get_test_name(test_file), test_file, content)

    def _get_test_cases_in_dir(self, directory=None, exclude=()):
        if directory is None:
            directory = '.'
        all_tests = [t for t in glob.glob(directory + '/vector[0-9]*.test')]
        tcs = list()
        for t in [
            t for t in all_tests if self._get_test_name(t) not in exclude
        ]:
            tcs.append(self._get_test_case_from_file(t))
        return tcs

    @staticmethod
    def _get_var_number(test_info_line):
        assert 'object' in test_info_line
        # Object number should be at end, e.g. 'object  1: ...'
        return test_info_line.split(':')[0].split(' ')[-1]

    def get_test_vector(self, test_case):
        test_info = [t for t in test_case.content.split('\n') if t]
        vector = utils.TestVector(test_case.name, test_case.origin)
        for idx, line in enumerate(test_info):
            # is in C hex notation, e.g. '0xffffff' (WITH the ''!)
            value = line.split(':')[1].strip()
            vector.add(value)

        return vector
