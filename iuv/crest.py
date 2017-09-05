from input_generation import BaseInputGenerator
from test_validation import TestValidator
import utils
import os
import logging
import re

bin_dir = os.path.abspath('./crest/bin')
lib_dir = os.path.abspath('./crest/lib')
include_dir = os.path.abspath('./crest/include')
name = 'crest'
test_name_pattern = re.compile('input[0-9]+$')


def get_test_cases(exclude=[]):
    all_tests = [t for t in os.listdir('.') if test_name_pattern.match(utils.get_file_name(t))]
    tcs = list()
    for t in [t for t in all_tests if utils.get_file_name(t) not in exclude]:
        with open(t, 'r') as inp:
            content = inp.read()
        tcs.append(utils.TestCase(utils.get_file_name(t), t, content))
    return tcs


class InputGenerator(BaseInputGenerator):

    def __init__(self, timelimit=None, log_verbose=False, search_heuristic='ppc', machine_model=utils.MACHINE_MODEL_32):
        super().__init__(timelimit, machine_model, log_verbose)
        self.log_verbose = log_verbose

        self._run_env = utils.get_env_with_path_added(bin_dir)

        self.search_heuristic = search_heuristic
        self.num_iterations = 100000

    def get_name(self):
        return name

    def get_run_env(self):
        return self._run_env

    def get_test_count(self):
        files = get_test_cases()
        if not files:
            raise utils.InputGenerationError('No test files generated.')
        return len(files)

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
        return method_type in ['_Bool',
                               'long long',
                               'long long int',
                               'long',
                               'long int',
                               'int',
                               'short',
                               'char',
                               'unsigned long long',
                               'unsigned long long int',
                               'unsigned long',
                               'unsigned long int',
                               'unsigned int',
                               'unsigned short',
                               'unsigned char']

    def _create_nondet_method(self, method_name, method_type, param_types):
        if not (method_type == 'void' or self.is_supported_type(method_type)):
            logging.warning('Crest can\'t handle symbolic values of type %s', method_type)
            internal_type = 'unsigned long long'
            logging.warning('Continuing with type %s for method %s', internal_type, method_name)
        elif method_type == '_Bool':
            internal_type = 'char'
        else:
            internal_type = method_type
        var_name = utils.get_sym_var_name(method_name)
        marker_method_call = 'CREST_' + '_'.join(internal_type.split())
        method_head = utils.get_method_head(method_name, method_type, param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += ['{0} {1};'.format(internal_type, var_name),
                            '{0}({1});'.format(marker_method_call, var_name)
                            ]

            if method_type == internal_type:
                method_body.append('return {0};'.format(var_name))
            else:
                method_body.append('return ({0}) {1};'.format(method_type, var_name))

        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename):
        compile_cmd = [os.path.join(bin_dir, 'crestc'),
                       filename]
        # the output file name created by crestc is 'input file name - '.c'
        instrumented_file = filename[:-2]
        input_gen_cmd = [os.path.join(bin_dir, 'run_crest'),
                         instrumented_file,
                         str(self.num_iterations),
                         '-' + self.search_heuristic]
        return [compile_cmd, input_gen_cmd]


class CrestTestValidator(TestValidator):

    def __init__(self, validation_config):
        super().__init__(validation_config)

    def get_name(self):
        return name

    def _get_test_vector(self, test):
        test_vector = utils.TestVector(test.name, test.origin)
        for line in test.content.split('\n'):
            value = line.strip()
            if value:
                test_vector.add(value)
        return test_vector

    def get_test_cases(self, exclude=[]):
        return get_test_cases(exclude)
