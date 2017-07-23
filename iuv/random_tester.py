import os
import logging
import glob
import utils
from input_generation import BaseInputGenerator
from test_validation import TestValidator

name = "random-testing"
include_dir = os.path.abspath("./random/include")
generator_harness = os.path.abspath("./random/random_tester.c")
random_runner = os.path.abspath("./random/run.sh")


def get_test_files(exclude=[], directory=utils.tmp):
    all_tests = [t for t in glob.glob(directory + '/vector[0-9]*.test')]
    return [t for t in all_tests if utils.get_file_name(t) not in exclude]


class InputGenerator(BaseInputGenerator):

    def get_run_env(self):
        return utils.get_env()

    def get_name(self):
        return name

    def prepare(self, filecontent):
        content = filecontent
        content += '\n'
        nondet_methods_used = utils.get_nondet_methods(filecontent)
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
        var_name = utils.get_sym_var_name(method_name)
        method_head = utils.get_method_head(method_name, method_type, param_types)
        method_body = ['{']
        if method_type != 'void':
            method_body += ['{0} {1};'.format(method_type, var_name),
                            'input(&{0}, sizeof({0}), \"{0}\");'.format(var_name),
                            'return {0};'.format(var_name)
                            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename):
        compiled_file = '.'.join(os.path.basename(filename).split('.')[:-1])
        compiled_file = utils.get_file_path(compiled_file, temp_dir=True)
        if '32' in self.machine_model:
            machinem_arg = "-m32"
        elif '64' in self.machine_model:
            machinem_arg = "-m64"
        else:
            raise AssertionError("Unknown machine model: " + self.machine_model)
        compile_cmd = ['gcc', machinem_arg, '-I', include_dir, '-o', compiled_file, generator_harness, filename]
        input_generation_cmd = [random_runner, compiled_file]

        return [compile_cmd, input_generation_cmd]

    def get_test_count(self):
        files = get_test_files()
        if not files:
            raise utils.InputGenerationError('No test files generated.')
        return len(files)


class RandomTestValidator(TestValidator):

    def get_name(self):
        return name

    def _get_var_number(self, test_info_line):
        assert 'object' in test_info_line
        return test_info_line.split(':')[0].split(' ')[-1]  # Object number should be at end, e.g. 'object  1: ...'

    def get_test_vector(self, test):
        with open(test, 'r') as inp:
            test_info = inp.readlines()
        vector = utils.TestVector(test)
        for idx, line in enumerate(test_info):
            var_name = line.split(':')[0].strip()  # Line format is var: value
            nondet_method_name = utils.get_corresponding_method_name(var_name)
            value = line.split(':')[1].strip()  # is in C hex notation, e.g. '\x00\x00' (WITH the ''!)
            vector.add(value, nondet_method_name)

        return vector if vector.vector else None

    def create_witness(self, filename, test_file, test_vector):
        witness = self.witness_creator.create_witness(producer=self.get_name(),
                                                      filename=filename,
                                                      test_vector=test_vector,
                                                      nondet_methods=utils.get_nondet_methods(filename),
                                                      machine_model=self.machine_model,
                                                      error_lines=self.get_error_lines(filename))

        test_name = '.'.join(os.path.basename(test_file).split('.')[:-1])
        witness_file = test_name + ".witness.graphml"
        witness_file = utils.get_file_path(witness_file)

        return {'name': witness_file, 'content': witness}

    def create_harness(self, filename, test_file, test_vector):
        harness = self.harness_creator.create_harness(nondet_methods=utils.get_nondet_methods(filename),
                                                      error_method=utils.error_method,
                                                      test_vector=test_vector)
        test_name = os.path.basename(test_file)
        harness_file = test_name + '.harness.c'
        harness_file = utils.get_file_path(harness_file)

        return {'name': harness_file, 'content': harness}

    def _create_all_x(self, filename, creator_method, visited_tests):
        created_content = []
        new_test_files = get_test_files(visited_tests)
        if len(new_test_files) > 0:
            logging.info("Looking at %s test files", len(new_test_files))
        empty_case_handled = False
        for test_file in new_test_files:
            logging.debug('Looking at test case %s', test_file)
            test_name = utils.get_file_name(test_file)
            assert test_name not in visited_tests
            assert os.path.exists(test_file)
            visited_tests.add(test_name)
            test_vector = self.get_test_vector(test_file)
            if test_vector or not empty_case_handled:
                if not test_vector:
                    test_vector = dict()
                    empty_case_handled = True
                new_content = creator_method(filename, test_file, test_vector)
                new_content['vector'] = test_vector
                new_content['origin'] = test_file
                created_content.append(new_content)
            else:
                logging.info("Test vector was not generated for %s", test_file)
        return created_content

    def create_all_witnesses(self, filename, visited_tests):
        return self._create_all_x(filename, self.create_witness, visited_tests)

    def create_all_harnesses(self, filename, visited_tests):
        return self._create_all_x(filename, self.create_harness, visited_tests)

    def get_test_files(self, exclude=[]):
        return get_test_files(exclude)


