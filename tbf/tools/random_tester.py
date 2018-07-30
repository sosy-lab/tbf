import os
import glob
import tbf.utils as utils
from tbf.input_generation import BaseInputGenerator
from tbf.test_validation import TestValidator
import pathlib

name = "prtest"
module_dir = pathlib.Path(__file__).resolve().parent
include_dir = module_dir / "random" / "include"
generator_harness = module_dir / "random" / "random_tester.c"
random_runner = module_dir / "random" / "run.sh"


class InputGenerator(BaseInputGenerator):

    def get_run_env(self):
        return utils.get_env()

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
                'input(&{0}, sizeof({0}), \"{0}\");'.format(var_name),
                'return {0};'.format(var_name)
            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename):
        compiled_file = '.'.join(os.path.basename(filename).split('.')[:-1])
        compiled_file = utils.get_file_path(compiled_file, temp_dir=True)
        machinem_arg = self.machine_model.compile_parameter
        compile_cmd = [
            'gcc', '-std=gnu11', machinem_arg, '-I', include_dir, '-o',
            compiled_file, generator_harness, filename, '-lm'
        ]
        input_generation_cmd = [random_runner, compiled_file]

        return [compile_cmd, input_generation_cmd]

    def get_test_cases(self, exclude=(), directory=utils.tmp):
        all_tests = [t for t in glob.glob(directory + '/vector[0-9]*.test')]
        tcs = list()
        for t in [
                t for t in all_tests if utils.get_file_name(t) not in exclude
        ]:
            with open(t, 'r') as inp:
                content = inp.read()
            tcs.append(utils.TestCase(utils.get_file_name(t), t, content))
        return tcs


class RandomTestValidator(TestValidator):

    def get_name(self):
        return name

    def _get_var_number(self, test_info_line):
        assert 'object' in test_info_line
        return test_info_line.split(':')[0].split(' ')[
            -1]  # Object number should be at end, e.g. 'object  1: ...'

    def _get_test_vector(self, test):
        test_info = [t for t in test.content.split('\n') if t]
        vector = utils.TestVector(test.name, test.origin)
        for idx, line in enumerate(test_info):
            var_name = line.split(':')[0].strip()  # Line format is var: value
            nondet_method_name = utils.get_corresponding_method_name(var_name)
            value = line.split(':')[1].strip(
            )  # is in C hex notation, e.g. '\x00\x00' (WITH the ''!)
            vector.add(value, nondet_method_name)

        return vector
