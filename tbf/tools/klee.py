import glob
import logging
import os

import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.testcase_converter import TestConverter

module_dir = os.path.dirname(os.path.realpath(__file__))
include_dir = os.path.join(module_dir, 'klee/include')
lib_dir = os.path.join(module_dir, 'klee/lib')
bin_dir = os.path.join(module_dir, 'klee/bin')
tests_dir = 'klee-tests'
klee_make_symbolic = 'klee_make_symbolic'
name = 'klee'


class InputGenerator(BaseInputGenerator):

    def __init__(self,
                 timelimit=None,
                 log_verbose=False,
                 additional_cli_options="",
                 machine_model=utils.MACHINE_MODEL_32):
        super().__init__(machine_model, log_verbose, additional_cli_options)
        self.log_verbose = log_verbose

        run_env = utils.get_env_with_path_added(bin_dir)
        run_env['KLEE_RUNTIME_LIBRARY_PATH'] = str(lib_dir)
        self._run_env = utils.add_ld_path_to_env(run_env, lib_dir)

        self.timelimit = timelimit if timelimit else 0

    def get_run_env(self):
        return self._run_env

    def get_name(self):
        return name

    def prepare(self, filecontent, nondet_methods_used):
        content = filecontent
        content += '\n'
        for method in nondet_methods_used:
            # append method definition at end of file content
            nondet_method_definition = self._get_nondet_method(method)
            content += nondet_method_definition
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
            method_body += [
                '{0} {1};'.format(method_type, var_name),
                'klee_make_symbolic(&{0}, sizeof({0}), \"{0}\");'.format(
                    var_name), 'return {0};'.format(var_name)
            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename, cli_options):
        if self.machine_model.is_32:
            mm_args = ['-arch', 'i386']
        elif self.machine_model.is_64:
            mm_args = ['-arch', 'x86_64']
        else:
            raise AssertionError("Unhandled machine model: " +
                                 self.machine_model.name)

        compiled_file = '.'.join(
            os.path.basename(filename).split('.')[:-1] + ['bc'])
        compile_cmd = ['clang'] + mm_args + [
            '-I', include_dir, '-emit-llvm', '-c', '-g', '-o', compiled_file,
            filename
        ]
        input_generation_cmd = ['klee']
        if self.timelimit > 0:
            input_generation_cmd += ['-max-time', str(self.timelimit)]
        input_generation_cmd.append('-only-output-states-covering-new')
        if cli_options:
            input_generation_cmd += cli_options
        if not cli_options or all("-search=" not in c for c in cli_options):
            input_generation_cmd += ['-search=random-path', '-search=nurs:covnew']
        input_generation_cmd += ['-output-dir=' + tests_dir]
        input_generation_cmd += [compiled_file]

        return [compile_cmd, input_generation_cmd]


class KleeTestConverter(TestConverter):

    def _get_test_cases_in_dir(self, directory=None, exclude=None):
        if directory is None:
            directory = tests_dir
        all_tests = [t for t in glob.glob(directory + '/*.ktest')]
        tcs = list()
        for t in [
            t for t in all_tests if self._get_test_name(t) not in exclude
        ]:
            tcs.append(self._get_test_case_from_file(t))
        return tcs

    def _get_test_case_from_file(self, test_file):
        file_name = self._get_test_name(test_file)
        with open(test_file, mode='rb') as inp:
            content = inp.read()
        return utils.TestCase(file_name, test_file, content)

    def get_test_vector(self, test):
        def _get_value(single_line):
            var_name = single_line.split(':')[2].strip()
            prefix_end = var_name.find("'")
            var_name = var_name[prefix_end + 1:-1]
            return var_name

        def _convert_bytestring_to_hex(bytestring):
            bytes = bytestring.split(r'\x')
            value = ''.join(reversed(bytes))
            value = '0x' + value
            return value

        def _get_var_number(test_info_line):
            assert 'object' in test_info_line
            # Object number should be at end, e.g. 'object  1: ...'
            return test_info_line.split(':')[0].split(' ')[-1]

        ktest_tool = [os.path.join(bin_dir, 'ktest-tool')]
        exec_output = utils.execute(
            ktest_tool + [test.origin], err_to_output=False, quiet=True)
        test_info = exec_output.stdout.split('\n')
        vector = utils.TestVector(test.name, test.origin)
        last_number = -1
        last_nondet_method = None
        last_value = None
        for line in [l for l in test_info if l.startswith('object')]:
            logging.debug("Looking at line: %s", line)
            if 'name:' in line:
                # assert len(line.split(':')) == 3
                var_number = int(_get_var_number(line))
                assert var_number > last_number
                last_number = var_number
                var_name = _get_value(line)
                assert last_nondet_method is None, \
                    "Last nondet method already or still assigned: %s" % last_nondet_method
                assert "'" not in var_name, \
                    "Variable name contains \"'\": %s" % var_name
                last_nondet_method = utils.get_corresponding_method_name(
                    var_name)
            elif 'data:' in line:
                # assert len(line.split(':')) == 3
                var_number = _get_var_number(line)
                assert last_nondet_method is not None
                # we get the value in bytestring notation, so we have to convert it afterwards
                value = _get_value(line)
                value = _convert_bytestring_to_hex(value)
                assert last_value is None
                last_value = str(value)
            if last_nondet_method is not None and last_value is not None:
                vector.add(last_value, last_nondet_method)
                last_nondet_method = None
                last_value = None

        return vector

    @staticmethod
    def _get_test_name(test_file):
        return os.path.basename(test_file)
