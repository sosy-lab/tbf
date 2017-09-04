import os
import utils
from input_generation import BaseInputGenerator
from test_validation import TestValidator

name = "fshell"
fshell_dir = os.path.abspath("./fshell")
bin_dir = os.path.join(fshell_dir, "bin")
fshell_binary = os.path.join(bin_dir, "fshell")
query_file = os.path.join(fshell_dir, "query-block-coverage")
tests_file = utils.get_file_path('testsuite.txt', temp_dir=True)


def get_test_cases(exclude=[]):
    if os.path.exists(tests_file):
        with open(tests_file, 'r') as inp:
            content = [l.strip() for l in inp.readlines()]
        if len([l for l in content if "Test Suite" in l]) > 1:
            raise AssertionError("More than one test suite exists in " + tests_file)

        curr_test = list()
        test_cases = list()
        count = 1
        for line in content:
            if line.startswith("IN:"):
                test_name = str(count)
                if test_name not in exclude:
                    test_cases.append(utils.TestCase(test_name, tests_file, curr_test))
                curr_test = list()
                count += 1
            if line.startswith("strto"):
                test_value = line.split("=")[1]
                curr_test.append(test_value)
        test_name = str(count)
        if curr_test and test_name not in exclude:
            test_cases.append(utils.TestCase(test_name, tests_file, curr_test))
        return test_cases
    else:
        return []


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
        method_head = utils.get_method_head(method_name, method_type, param_types)
        method_body = ['{']
        if method_type != 'void':
            if 'float' in method_type or 'double' in method_type:
                conversion_cmd = 'strtold({0}, 0);'.format(var_name)
            elif 'unsigned' in method_type and 'long long' in method_type:
                conversion_cmd = 'strtoull({0}, 0, 10);'.format(var_name)
            else:
                conversion_cmd = 'strtoll({0}, 0, 10);'.format(var_name)
            return_statement = 'return ({0}) {1}'.format(method_type, conversion_cmd)
            method_body += ['char * {0} = malloc(1000);'.format(var_name),
                            'fgets({0}, 1000, stdin);'.format(var_name),
                            return_statement
                            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def _get_error_method_dummy(self):
        # overwrite the default error method dummy to *not* exit. Somehow, Fshell doesn't like exit or aborts.
        return 'void ' + utils.error_method + '() {{ fprintf(stderr, \"{0}\\n\"); }}\n'.format(utils.error_string)

    def create_input_generation_cmds(self, filename):
        if self.machine_model.is_32:
            mm_arg = "--32"
        elif self.machine_model.is_64:
            mm_arg = "--64"
        else:
            raise AssertionError("Unhandled machine model " + self.machine_model)

        input_generation_cmd = [fshell_binary,
                                mm_arg,
                                "--outfile", tests_file,
                                "--query-file", query_file,
                                filename]

        return [input_generation_cmd]

    def get_test_count(self):
        test_cases = get_test_cases()
        if not test_cases:
            raise utils.InputGenerationError('No tests generated.')
        return len(test_cases)


class FshellTestValidator(TestValidator):

    def get_name(self):
        return name

    def get_test_vector(self, test):
        vector = utils.TestVector(test.name, test.origin)
        for tv in test.content:
            vector.add(tv)

        return vector

    def get_test_cases(self, exclude=[]):
        return get_test_cases(exclude)


