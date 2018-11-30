import os

import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

module_dir = os.path.dirname(os.path.realpath(__file__))
base_dir = os.path.join(module_dir, 'cpatiger')
binary_dir = os.path.join(base_dir, 'scripts')
binary = os.path.join(binary_dir, 'cpa.sh')
tests_dir = 'output'
input_method = 'input'
name = 'cpatiger'


class InputGenerator(BaseInputGenerator):

    def __init__(self,
                 timelimit=None,
                 log_verbose=False,
                 additional_cli_options='',
                 machine_model=utils.MACHINE_MODEL_32):
        super().__init__(machine_model, log_verbose, additional_cli_options)

        self._run_env = utils.get_env_with_path_added(binary_dir)
        # Make sure that timelimit is never None
        self.timelimit = timelimit if timelimit else 0

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
        method_head = utils.get_method_head(method_name, method_type, param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += [
                'return ({0}) {1}();'.format(method_type, input_method)
            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename, cli_options):
        import shutil
        config_copy_dir = 'config'
        if not os.path.exists(config_copy_dir):
            copy_dir = os.path.join(base_dir, 'config')
            shutil.copytree(copy_dir, config_copy_dir)

        input_generation_cmd = [binary]
        if self.timelimit > 0:
            input_generation_cmd += ['-timelimit', str(self.timelimit)]
        if not cli_options or '-tiger-variants' not in cli_options:
            input_generation_cmd += ['-tiger-variants']
        input_generation_cmd += ['-outputpath', tests_dir, '-spec',
                                 utils.spec_file
                                 ]
        if cli_options:
            input_generation_cmd += cli_options
        input_generation_cmd.append(filename)

        return [input_generation_cmd]


class CpaTigerTestConverter(TestConverter):

    def _get_test_cases_in_dir(self, directory=None, exclude=()):
        if directory is None:
            directory = tests_dir
        tests_file = os.path.join(directory, 'testsuite.txt')
        if os.path.exists(tests_file):
            with open(tests_file, 'r') as inp:
                tests = [
                    l.strip()
                    for l in inp.readlines()
                    if l.strip().startswith('[') and l.strip().endswith(']')
                ]
            tests = [t for i, t in enumerate(tests) if str(i) not in exclude]
            tcs = list()
            for i, t in enumerate(tests):
                tcs.append(utils.TestCase(str(i), tests_file, t))
            return tcs
        else:
            return []

    def _get_test_case_from_file(self, test_file):
        """
        Not supported. It is not possible to create a single test case.

        see _get_test_cases_in_dir instead.

        :raises NotImplementedError: when called
        """
        raise NotImplementedError("CPATiger can only create test cases for the full test suite")

    def get_test_vector(self, test_case):
        assert len(test_case.content.split('\n')) == 1
        assert test_case.content.startswith('[') and test_case.content.endswith(']')
        test_vector = utils.TestVector(test_case.name, test_case.origin)
        processed_line = test_case.content[1:-1]
        test_values = processed_line.split(', ')
        for value in test_values:
            test_vector.add(value)
        return test_vector
