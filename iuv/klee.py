from input_generation import BaseInputGenerator
from test_validation import TestValidator
import utils
import glob
import os
import logging

include_dir = os.path.abspath('./klee/include/')
lib_dir = os.path.abspath('./klee/lib')
bin_dir = os.path.abspath('./klee/bin')
tests_output = utils.tmp
tests_dir = os.path.join(tests_output, 'klee-tests')
klee_make_symbolic = 'klee_make_symbolic'
name = 'klee'


def get_test_files(exclude=[]):
    all_tests = [t for t in glob.glob(tests_dir + '/*.ktest')]
    if not all_tests:
        raise utils.InputGenerationError('No test files generated.')
    return [t for t in all_tests if utils.get_file_name(t) not in exclude]


class InputGenerator(BaseInputGenerator):

    def __init__(self, timelimit=0, log_verbose=False, search_heuristic=['random-path', 'nurs:covnew'], machine_model='32bit'):
        super().__init__(timelimit, machine_model)
        self.log_verbose = log_verbose
        if type(search_heuristic) is not list:
            self.search_heuristic = list(search_heuristic)
        else:
            self.search_heuristic = search_heuristic

        self._run_env = utils.get_env_with_path_added(bin_dir)

    def get_run_env(self):
        return self._run_env

    def get_name(self):
        return name

    def prepare(self, filecontent):
        content = filecontent
        content += '\n'
        nondet_methods_used = utils.get_undefined_methods(filecontent)
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
                            'klee_make_symbolic(&{0}, sizeof({0}), \"{0}\");'.format(var_name),
                            'return {0};'.format(var_name)
                            ]
        method_body = '\n    '.join(method_body)
        method_body += '\n}\n'

        return method_head + method_body

    def create_input_generation_cmds(self, filename):
        compiled_file = '.'.join(os.path.basename(filename).split('.')[:-1] + ['bc'])
        compiled_file = utils.get_file_path(compiled_file, temp_dir=True)
        compile_cmd = ['clang', '-I', include_dir, '-emit-llvm', '-c', '-g', '-o', compiled_file, filename]
        input_generation_cmd = ['klee']
        if self.timelimit > 0:
            input_generation_cmd += ['-max-time', str(self.timelimit)]
        input_generation_cmd.append('-only-output-states-covering-new')
        input_generation_cmd += ['-search=' + h for h in self.search_heuristic]
        input_generation_cmd += ['-output-dir=' + tests_dir]
        input_generation_cmd += [compiled_file]

        return [compile_cmd, input_generation_cmd]

    def get_test_count(self):
        return len(get_test_files())


class KleeTestValidator(TestValidator):

    def get_name(self):
        return name

    def _get_var_number(self, test_info_line):
        assert 'object' in test_info_line
        return test_info_line.split(':')[0].split(' ')[-1]  # Object number should be at end, e.g. 'object  1: ...'

    def get_test_vector(self, test):
        ktest_tool = [os.path.join(bin_dir, 'ktest-tool')]
        exec_output = utils.execute(ktest_tool + [test], err_to_output=False, quiet=True)
        test_info = exec_output.stdout.split('\n')
        objects = dict()
        for line in [l for l in test_info if l.startswith('object')]:
            if 'name:' in line:
                #assert len(line.split(':')) == 3
                var_number = self._get_var_number(line)
                var_name = line.split(':')[2][2:-1]  # [1:-1] to cut the surrounding ''
                if var_number not in objects.keys():
                    objects[var_number] = dict()
                nondet_method_name = utils.get_corresponding_method_name(var_name)
                objects[var_number]['name'] = nondet_method_name
            elif 'data:' in line:
                #assert len(line.split(':')) == 3
                var_number = self._get_var_number(line)
                value = line.split(':')[-1].strip()  # is in C hex notation, e.g. '\x00\x00' (WITH the ''!)
                objects[var_number]['value'] = value

        return objects if objects.keys() else None

    def create_witness(self, filename, test_file, test_vector):
        witness = self.witness_creator.create_witness(producer=self.get_name(),
                                                      filename=filename,
                                                      test_vector=test_vector,
                                                      nondet_methods=utils.get_undefined_methods(filename),
                                                      machine_model=self.machine_model,
                                                      error_line=self.get_error_line(filename))

        test_name = '.'.join(os.path.basename(test_file).split('.')[:-1])
        witness_file = test_name + ".witness.graphml"
        witness_file = utils.get_file_path(witness_file, temp_dir=False)

        return {'name': witness_file, 'content': witness}

    def create_harness(self, filename, test_file, test_vector):
        harness = self.harness_creator.create_harness(producer=self.get_name(),
                                                      filename=filename,
                                                      test_vector=test_vector,
                                                      nondet_methods=utils.get_undefined_methods(filename),
                                                      error_method=utils.error_method)
        test_name = os.path.basename(test_file)
        harness_file = test_name + '.harness.c'
        harness_file = utils.get_file_path(harness_file, temp_dir=False)

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
                new_content = creator_method(filename, test_file, test_vector)
                new_content['vector'] = test_vector
                created_content.append(new_content)
            else:
                logging.info("Test vector was not generated for %s", test_file)
        return created_content

    def create_all_witnesses(self, filename, visited_tests):
        return self._create_all_x(filename, self.create_witness, visited_tests)

    def create_all_harnesses(self, filename, visited_tests):
        return self._create_all_x(filename, self.create_harness, visited_tests)
