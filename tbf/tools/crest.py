import logging
import os
import re

import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

module_dir = os.path.dirname(os.path.realpath(__file__))
bin_dir = os.path.join(module_dir, 'crest/bin')
lib_dir = os.path.join(module_dir, 'crest/lib')
include_dir = os.path.join(module_dir, 'crest/include')
name = 'crest'
test_name_pattern = re.compile('input[0-9]+$')
tests_dir = '.'


class InputGenerator(BaseInputGenerator):

    def __init__(self,
                 log_verbose=False,
                 additional_cli_options="",
                 machine_model=utils.MACHINE_MODEL_32):
        super().__init__(machine_model, log_verbose, additional_cli_options)
        self.log_verbose = log_verbose

        self._run_env = utils.get_env_with_path_added(bin_dir)
        self._run_env = utils.add_ld_path_to_env(self._run_env, lib_dir)

        self.num_iterations = 100000

    def get_name(self):
        return name

    def get_run_env(self):
        return self._run_env

    def prepare(self, filecontent, nondet_methods_used):
        content = ''
        for line in filecontent.split('\n'):
            prepared_line = line
            if '//' in prepared_line:
                start = prepared_line.find('//')
                prepared_line = prepared_line[:start]
            content += prepared_line + '\n'
        content = '#include<crest.h>\n' + content
        content += '\n'
        for method in nondet_methods_used:  # append method definition at end of file content
            nondet_method_definition = self._get_nondet_method(method)
            content += nondet_method_definition
        return content

    def _get_nondet_method(self, method_information):
        method_name = method_information['name']
        m_type = method_information['type']
        param_types = method_information['params']
        return self._create_nondet_method(method_name, m_type, param_types)

    def is_supported_type(self, method_type):
        return method_type in [
            '_Bool', 'long long', 'long long int', 'long', 'long int', 'int',
            'short', 'char', 'unsigned long long', 'unsigned long long int',
            'unsigned long', 'unsigned long int', 'unsigned int',
            'unsigned short', 'unsigned char'
        ]

    def _create_nondet_method(self, method_name, method_type, param_types):
        if not (method_type == 'void' or self.is_supported_type(method_type)):
            logging.warning('Crest can\'t handle symbolic values of type %s',
                            method_type)
            internal_type = 'unsigned long long'
            logging.warning('Continuing with type %s for method %s',
                            internal_type, method_name)
        elif method_type == '_Bool':
            internal_type = 'char'
        else:
            internal_type = method_type
        var_name = utils.get_sym_var_name(method_name)
        marker_method_call = 'CREST_' + '_'.join(internal_type.split())
        method_head = utils.get_method_head(method_name, method_type,
                                            param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += [
                '{0} {1};'.format(internal_type, var_name), '{0}({1});'.format(
                    marker_method_call, var_name)
            ]

            if method_type == internal_type:
                method_body.append('return {0};'.format(var_name))
            else:
                method_body.append('return ({0}) {1};'.format(
                    method_type, var_name))

        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename, cli_options):
        compile_cmd = [os.path.join(bin_dir, 'crestc'), filename]
        # the output file name created by crestc is 'input file name - '.c'
        instrumented_file = os.path.abspath(filename[:-2])
        input_gen_cmd = [
            os.path.join(bin_dir, 'run_crest'), instrumented_file,
            str(self.num_iterations)
        ]
        if cli_options:
            input_gen_cmd += cli_options
        else:
            input_gen_cmd.append('-ppc')
        return [compile_cmd, input_gen_cmd]


class CrestTestConverter(TestConverter):

    def _get_test_cases_in_dir(self, directory=None, exclude=None):
        if directory is None:
            directory = tests_dir
        all_tests = [
            t for t in os.listdir(directory)
            if test_name_pattern.match(utils.get_file_name(t))
        ]
        tcs = list()
        for t in [
            t for t in all_tests if utils.get_file_name(t) not in exclude
        ]:
            tcs.append(self._get_test_case_from_file(t))
        return tcs

    def _get_test_case_from_file(self, test_file):
        with open(test_file, 'r') as inp:
            content = inp.read()
        return utils.TestCase(utils.get_file_name(test_file), test_file, content)

    def get_test_vector(self, test_case):
        test_vector = utils.TestVector(test_case.name, test_case.origin)
        for line in test_case.content.split('\n'):
            value = line.strip()
            if value:
                test_vector.add(value)
        return test_vector
