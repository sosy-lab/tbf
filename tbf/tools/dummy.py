import tbf.utils as utils
from tbf.harness_generation import HarnessCreator
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_validation import TestValidator as BaseTestValidator

name = "Dummy"


class InputGenerator(BaseInputGenerator):

    def create_input_generation_cmds(self, program_file, cli_options):
        instrumented_program = './tested.out'
        compiler = "gcc"
        compile_cmd = [compiler, self.machine_model.compile_parameter, program_file]

        return [compile_cmd]

    def get_run_env(self):
        return utils.get_env()

    def get_name(self):
        return name

    def prepare(self, filecontent, nondet_methods_used):
        harness = ""
        for nondet_method in nondet_methods_used:
            harness = harness + self._get_nondet_method(nondet_method)
        return filecontent + '\n' + harness

    def _get_nondet_method(self, method_information):
        method_name = method_information['name']
        m_type = method_information['type']
        param_types = method_information['params']
        return self._create_nondet_method(method_name, m_type, param_types)

    def _create_nondet_method(self, method_name, method_type, param_types):
        method_head = utils.get_method_head(method_name, 'int', param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += [
                'return 0;'
            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def get_test_cases(self, exclude=(), directory=None):
        return list()


class TestValidator(BaseTestValidator):

    def _get_test_vector(self, test_case, nondet_methods):
        raise NotImplementedError("Should never be called")

    def get_name(self):
        return name

    def get_test_vector(self, test_case, nondet_methods):
        raise NotImplementedError("Should never be called")
