from input_generation import BaseInputGenerator
from test_validation import TestValidator
import utils
import os
import logging

base_dir = os.path.abspath('./cpatiger')
binary_dir = os.path.join(base_dir, 'scripts')
binary = os.path.join(binary_dir, 'cpa.sh')
tests_dir = os.path.join(utils.tmp, 'output')
tests_file = os.path.join(tests_dir, 'testsuite.txt')
input_method = 'input'
name = 'CPATiger'


def get_test_cases(exclude=[]):
    if os.path.exists(tests_file):
        with open(tests_file, 'r') as inp:
            tests = [l for l in inp.readlines()
                     if l.strip().startswith('[') and l.strip().endswith(']')]
        return [t for t in tests if t not in exclude]
    else:
        return []


class InputGenerator(BaseInputGenerator):

    def __init__(self, timelimit=0, log_verbose=False, machine_model='32bit'):
        super().__init__(timelimit, machine_model)
        self.log_verbose = log_verbose

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

    def get_test_count(self):
        return len(get_test_cases())


class CpaTigerTestValidator(TestValidator):

    def get_name(self):
        return name

    def get_test_vectors(self, test):
        vectors = list()
        with open(test, 'r') as inp:
            for line in inp.readlines():
                processed_line = line.strip()
                if processed_line.startswith('[') and processed_line.endswith(']'):
                    test_vector = utils.TestVector(test)
                    processed_line = processed_line[1:-1]
                    test_values = processed_line.split(', ')
                    for value in test_values:
                        test_vector.add(value)
                    vectors.append(test_vector)
        return vectors

    def create_witness(self, filename, test_name, test_vector, nondet_methods):
        """
        Creates a witness for the test file produced by crest.
        Test files produced by our version of crest specify one test value per line, without
        any mention of the variable the value is assigned to.
        Because of this, we have to build a fancy witness automaton of the following format:
        For each test value specified in the test file, there is one precessor and one
        successor state. These two states are connected by one transition for each
        call to a CREST_x(..) function. Each of these transitions has the assumption,
        that the variable specified in the corresponding CREST_x(..) function has the current
        test value.
        """
        witness = self.witness_creator.create_witness(producer=self.get_name(),
                                                      filename=filename,
                                                      test_vector=test_vector,
                                                      nondet_methods=nondet_methods,
                                                      machine_model=self.machine_model,
                                                      error_lines=self.get_error_lines(filename))

        witness_file = test_name + ".witness.graphml"
        witness_file = utils.get_file_path(witness_file)

        return {'name': witness_file, 'content': witness}

    def create_harness(self, filename, test_name, test_vector, nondet_methods):
        harness = self.harness_creator.create_harness(nondet_methods=nondet_methods,
                                                      error_method=utils.error_method,
                                                      test_vector=test_vector)


        harness_file = test_name + '.harness.c'
        harness_file = utils.get_file_path(harness_file)

        return {'name': harness_file, 'content': harness}

    def _create_all_x(self, filename, creation_method, nondet_methods, visited_tests=None):
        if visited_tests:
            raise utils.ConfigError("CPATiger can't create test cases in parallel to validation.")
        created_content = []
        empty_case_handled = False
        vectors = self.get_test_vectors(tests_file)

        for count, test_vector in enumerate(vectors):
            if test_vector or not empty_case_handled:
                testname = 'test{0}'.format(count)
                if not test_vector:
                    test_vector = dict()
                    empty_case_handled = True
                new_content = creation_method(filename, testname, test_vector, nondet_methods)
                new_content['vector'] = test_vector
                new_content['origin'] = tests_file
                created_content.append(new_content)
            else:
                logging.debug("Test vector was not generated", )
        return created_content

    def create_all_test_vectors(self, filename, visited_tests):
        vectors = self.get_test_vectors(tests_file)
        return vectors

    def create_all_witnesses(self, filename, visited_tests, nondet_methods):
        return self._create_all_x(filename, self.create_witness, visited_tests, nondet_methods)

    def create_all_harnesses(self, filename, visited_tests, nondet_methods):
        return self._create_all_x(filename, self.create_harness, visited_tests, nondet_methods)

    def get_test_files(self, exclude=[]):
        return get_test_cases(exclude)
