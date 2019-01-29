import os

import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

name = "fshell"
module_dir = os.path.dirname(os.path.realpath(__file__))
fshell_dir = os.path.join(module_dir, "fshell")
bin_dir = os.path.join(fshell_dir, "bin")
fshell_binary = os.path.join(bin_dir, "fshell")
query_file = os.path.join(fshell_dir, "query-block-coverage")
tests_dir = '.'
tests_file = os.path.join(tests_dir, 'testsuite.txt')


class Preprocessor:

    def prepare(self, filecontent, nondet_methods_used, error_method=None):
        content = filecontent
        content += '\n'
        content += utils.EXTERNAL_DECLARATIONS
        content += '\n'
        content += utils.get_assume_method()
        content += '\n'
        if error_method:
            content += self._get_error_method_definition(error_method)

        # FShell ignores methods starting with 'nondet' and '__VERIFIER_nondet'.
        # => rename them so that they are analyzed correctly
        content = content.replace("nondet", "_nondet")

        return content

    @staticmethod
    def _get_error_method_definition(error_method):
        return "void {}() {{ fprintf(stderr, \"{}\\n\"); }}\n".format(error_method, utils.ERROR_STRING)


class InputGenerator(BaseInputGenerator):

    def __init__(self, machine_model, log_verbose, additional_options):
        super().__init__(machine_model, log_verbose, additional_options, Preprocessor())

    def get_run_env(self):
        return utils.get_env_with_path_added(bin_dir)

    def get_name(self):
        return name

    def create_input_generation_cmds(self, filename, cli_options):
        if self.machine_model.is_32:
            mm_arg = "--32"
        elif self.machine_model.is_64:
            mm_arg = "--64"
        else:
            raise AssertionError("Unhandled machine model " +
                                 self.machine_model)

        input_generation_cmd = [
            fshell_binary, mm_arg, "--outfile", tests_file, "--query-file",
            query_file
        ]
        if cli_options:
            input_generation_cmd += cli_options
        input_generation_cmd += [filename]

        return [input_generation_cmd]


class FshellTestConverter(TestConverter):

    def __init__(self, nondet_methods):
        self._interesting_methods = [m['name'].replace('nondet', '_nondet') for m in nondet_methods]

    def _get_test_cases_in_dir(self, directory=None, exclude=None):
        if directory is None:
            directory = tests_dir
        tests_file = os.path.join(directory, 'testsuite.txt')
        if os.path.exists(tests_file):
            with open(tests_file, 'r') as inp:
                content = [l.strip() for l in inp.readlines()]
            if len([l for l in content if "Test Suite" in l]) > 1:
                raise AssertionError("More than one test suite exists in " +
                                     tests_file)

            curr_test = list()
            test_cases = list()
            count = 0
            for line in content:
                if line.startswith("IN:"):
                    test_name = str(count)
                    if test_name not in exclude and count > 0:
                        test_cases.append(
                            utils.TestCase(test_name, tests_file, curr_test))
                    curr_test = list()
                    count += 1
                if any(line.startswith(m + '(') for m in self._interesting_methods):
                    test_value = line.split("=")[1]
                    curr_test.append(test_value)
            test_name = str(count)
            if curr_test and test_name not in exclude:
                test_cases.append(
                    utils.TestCase(test_name, tests_file, curr_test))
            return test_cases
        else:
            return []

    def _get_test_case_from_file(self, test_file):
        """
        Not supported. It is not possible to create a single test case.

        see _get_test_cases_in_dir instead.

        :raises NotImplementedError: when called
        """
        raise NotImplementedError("FShell can only create test cases for the full test suite")

    def get_test_vector(self, test_case):
        vector = utils.TestVector(test_case.name, test_case.origin)
        for tv in test_case.content:
            vector.add(tv)

        return vector
