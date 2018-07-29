from tbf.input_generation import BaseInputGenerator
from tbf.test_validation import TestValidator
import tbf.utils as utils
import os
import logging

base_dir = os.path.abspath('./cpatiger')
binary_dir = os.path.join(base_dir, 'scripts')
binary = os.path.join(binary_dir, 'cpa.sh')
tests_dir = os.path.join(utils.tmp, 'output')
input_method = 'input'
name = 'cpatiger'


class InputGenerator(BaseInputGenerator):

    def __init__(self, timelimit=0, log_verbose=False, machine_model=utils.MACHINE_MODEL_32):
        super().__init__(timelimit, machine_model, log_verbose)

        self._run_env = utils.get_env_with_path_added(binary_dir)

    def get_run_env(self):
        return self._run_env

    def get_name(self):
        return name

    def prepare(self, filecontent, nondet_methods_used):
        content = filecontent
        content += '\n'
        content += 'extern int input();\n'
        for method in nondet_methods_used:  # append method definition at end of file content
            nondet_method_definition = self._get_nondet_method(method)
            content += nondet_method_definition
        return content

    def _get_nondet_method(self, method_information):
        method_name = method_information['name']
        m_type = method_information['type']
        param_types = method_information['params']
        return self._create_nondet_method(method_name, m_type, param_types)

    def _create_nondet_method(self, method_name, method_type, param_types):
        method_head = utils.get_method_head(method_name, 'int', param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += ['return ({0}) {1}();'.format(method_type, input_method)]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename):
        import shutil
        config_copy_dir = utils.get_file_path('config', temp_dir=True)
        if not os.path.exists(config_copy_dir):
            copy_dir = os.path.join(base_dir, 'config')
            shutil.copytree(copy_dir, config_copy_dir)

        input_generation_cmd = [binary]
        if self.timelimit > 0:
            input_generation_cmd += ['-timelimit', str(self.timelimit)]
        input_generation_cmd += ['-tiger-variants',
                                 '-outputpath', tests_dir,
                                 '-spec', utils.spec_file,
                                 filename]

        return [input_generation_cmd]

    def get_test_cases(self, exclude=(), directory=tests_dir):
        tests_file = os.path.join(directory, 'testsuite.txt')
        if os.path.exists(tests_file):
            with open(tests_file, 'r') as inp:
                tests = [l.strip() for l in inp.readlines()
                         if l.strip().startswith('[') and l.strip().endswith(']')]
            tests = [t for i, t in enumerate(tests) if str(i) not in exclude]
            tcs = list()
            for i, t in enumerate(tests):
                tcs.append(utils.TestCase(str(i), tests_file, t))
            return tcs
        else:
            return []

class CpaTigerTestValidator(TestValidator):

    def _get_test_vector(self, test):
        assert len(test.content.split('\n')) == 1
        assert test.content.startswith('[') and test.content.endswith(']')
        test_vector = utils.TestVector(test.name, test.origin)
        processed_line = test.content[1:-1]
        test_values = processed_line.split(', ')
        for value in test_values:
            test_vector.add(value)
        return test_vector

    def get_name(self):
        return name
