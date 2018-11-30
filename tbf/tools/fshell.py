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


class InputGenerator(BaseInputGenerator):

    def get_run_env(self):
        return utils.get_env_with_path_added(bin_dir)

    def get_name(self):
        return name

    def prepare(self, filecontent, nondet_methods_used):
        content = filecontent
        content += '\n'
        for m in nondet_methods_used:
            content += self._get_nondet_method(m)

        # FShell ignores __VERIFIER_nondet methods. We rename them so that they are analyzed correctly
        content = content.replace("__VERIFIER_", "___VERIFIER_")

        return content

    def _get_nondet_method(self, method_information):
        method_name = method_information['name']
        m_type = method_information['type']
        param_types = method_information['params']
        return self._create_nondet_method(method_name, m_type, param_types)

    def _create_nondet_method(self, method_name, method_type, param_types):
        var_name = utils.get_sym_var_name(method_name)
        method_head = utils.get_method_head(method_name, method_type,
                                            param_types)
        method_body = ['{']
        if method_type != 'void':
            if 'float' in method_type or 'double' in method_type:
                conversion_cmd = 'strtold({0}, 0);'.format(var_name)
            elif 'unsigned' in method_type and 'long long' in method_type:
                conversion_cmd = 'strtoull({0}, 0, 10);'.format(var_name)
            else:
                conversion_cmd = 'strtoll({0}, 0, 10);'.format(var_name)
            return_statement = 'return ({0}) {1}'.format(
                method_type, conversion_cmd)
            method_body += [
                'char * {0} = malloc(1000);'.format(var_name),
                'fgets({0}, 1000, stdin);'.format(var_name), return_statement
            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def _get_error_method_dummy(self, error_method):
        # overwrite the default error method dummy to *not* exit. Somehow, Fshell doesn't like exit or aborts.
        return 'void ' + error_method + '() {{ fprintf(stderr, \"{0}\\n\"); }}\n'.format(
            utils.error_string)

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
            count = 1
            for line in content:
                if line.startswith("IN:"):
                    test_name = str(count)
                    if test_name not in exclude:
                        test_cases.append(
                            utils.TestCase(test_name, tests_file, curr_test))
                    curr_test = list()
                    count += 1
                if line.startswith("strto"):
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
