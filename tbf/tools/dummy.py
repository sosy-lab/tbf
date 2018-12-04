import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

name = "Dummy"


class Preprocessor:

    def prepare(self, filecontent,  nondet_methods_used, error_method=None):
        content = filecontent
        content += '\n'
        content += utils.EXTERNAL_DECLARATIONS
        content += '\n'
        content += utils.get_assume_method()
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
        method_head = utils.get_method_head(method_name, method_type, param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += [
                'return *(({}*) 0);'.format(method_type)
            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body


class InputGenerator(BaseInputGenerator):

    def __init__(self, machine_model, log_verbose, additional_options):
        super().__init__(machine_model, log_verbose, additional_options, Preprocessor())

    def create_input_generation_cmds(self, program_file, cli_options):
        instrumented_program = './tested.out'
        compiler = "gcc"
        compile_cmd = [compiler, self.machine_model.compile_parameter, program_file]

        return [compile_cmd]

    def get_run_env(self):
        return utils.get_env()

    def get_name(self):
        return name


class DummyTestConverter(TestConverter):

    def _get_test_cases_in_dir(self, directory=None, exclude=None):
        return ()

    def _get_test_case_from_file(self, test_file):
        raise NotImplementedError("Should never be called")

    def get_test_vector(self, test_case):
        raise NotImplementedError("Should never be called")
