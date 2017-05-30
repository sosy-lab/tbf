from input_generation import BaseInputGenerator
from test_validation import TestValidator
import utils
import glob
import os
import ast_visitor
from ast_visitor import NondetReplacer
from pycparser import c_ast as a
import pycparser

include_dir = os.path.abspath('./klee/include/')
lib_dir = os.path.abspath('./klee/lib')
bin_dir = os.path.abspath('./klee/bin')
tests_output = utils.tmp
tests_dir = os.path.join(tests_output, 'klee-tests')
klee_make_symbolic = 'klee_make_symbolic'
name = 'klee'
sym_var_prefix = '__sym_'


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
        nondet_methods_used = utils.get_nondet_methods(filecontent)
        for method in nondet_methods_used:  # append method definition at end of file content
            nondet_method_definition = self._get_nondet_method(method)
            content += nondet_method_definition
        return content

    def _get_nondet_method(self, method_name):
        assert method_name.startswith('__VERIFIER_nondet_')
        m_type = method_name[len('__VERIFIER_nondet_'):]
        if m_type[0] == 'u' and m_type != 'unsigned':  # resolve uint to unsigned int (e.g.)
            m_type = 'unsigned ' + m_type[1:]
        elif m_type == 'pointer':
            m_type = 'void *'
        return self._create_nondet_method(method_name, m_type)

    def _create_nondet_method(self, method_name, method_type):
        var_name = sym_var_prefix + method_name[len('__VERIFIER_nondet_'):]
        return '{0} {1}() {{\n    {0} {2};\n    klee_make_symbolic(&{2}, sizeof({2}), \"{2}\");\n    return {2};\n}}\n'.\
            format(method_type, method_name, var_name)

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

    def get_ast_replacer(self):
        return None



class AstReplacer(NondetReplacer):

    def _get_amper(self, var_name):
        return a.UnaryOp('&', a.ID(var_name))

    def _get_sizeof_call(self, var_name):
        return a.UnaryOp('sizeof', a.ID(var_name))

    def _get_string(self, string):
        return a.Constant('string', '\"' + string + '\"')

    # Hook
    def get_nondet_marker(self, var_name, var_type):
        parameters = [self._get_amper(var_name), self._get_sizeof_call(var_name), self._get_string(var_name)]
        return a.FuncCall(a.ID(klee_make_symbolic), a.ExprList(parameters))

    # Hook
    def get_error_stmt(self):
        parameters = [a.Constant('int', str(utils.error_return))]
        return a.FuncCall(a.ID('exit'), a.ExprList(parameters))

    # Hook
    def get_preamble(self):
        parser = pycparser.CParser()
        # Define dummy klee_make_symbolic
        definitions = 'typedef unsigned long int size_t;'
        make_symbolic_def = 'void klee_make_symbolic(void *addr, size_t type, const char *name) { }'
        full_preamble = '\n'.join([definitions, make_symbolic_def])
        ast = parser.parse(full_preamble)
        return ast.ext


class KleeTestValidator(TestValidator):

    def get_name(self):
        return name

    def _get_var_number(self, test_info_line):
        assert 'object' in test_info_line
        return test_info_line.split(':')[0].split(' ')[-1]  # Object number should be at end, e.g. 'object  1: ...'

    def get_test_vector(self, test):
        ktest_tool = [os.path.join(bin_dir, 'ktest-tool'), '--write-ints']
        exec_output = utils.execute(ktest_tool + [test], err_to_output=False, quiet=True)
        test_info = exec_output.stdout.split('\n')
        objects = dict()
        for line in [l for l in test_info if l.startswith('object')]:
            if 'name:' in line:
                assert len(line.split(':')) == 3
                var_number = self._get_var_number(line)
                var_name = line.split(':')[2][2:-1]  # [1:-1] to cut the surrounding ''
                if var_number not in objects.keys():
                    objects[var_number] = dict()
                nondet_method_name = self._get_nondet_method_name(var_name)
                objects[var_number]['name'] = nondet_method_name

            elif 'data:' in line:
                assert len(line.split(':')) == 3
                var_number = self._get_var_number(line)
                value = line.split(':')[-1].strip()
                objects[var_number]['value'] = value

        return objects

    def _get_nondet_method_name(self, nondet_var_name):
        return '__VERIFIER_nondet_' + nondet_var_name[len(sym_var_prefix):]

    def create_witness(self, filename, test_file, test_vector):
        witness = self.witness_creator.create_witness(producer=self.get_name(),
                                                      filename=filename,
                                                      test_vector=test_vector,
                                                      nondet_methods=utils.get_nondet_methods(filename),
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
                                                      nondet_methods=utils.get_nondet_methods(filename),
                                                      error_method=utils.error_method)
        test_name = os.path.basename(test_file)
        harness_file = test_name + '.harness.c'
        harness_file = utils.get_file_path(harness_file, temp_dir=False)

        return {'name': harness_file, 'content': harness}

    def _create_all_x(self, filename, creator_method, visited_tests):
        created_content = []
        for test in glob.iglob(tests_dir + '/*.ktest'):
            test_name = test.split('/')[-1]
            if test_name in visited_tests:
                continue
            else:
                visited_tests.add(test_name)
            test_vector = self.get_test_vector(test)
            new_content = creator_method(filename, test, test_vector)
            created_content.append(new_content)
        return created_content

    def create_all_witnesses(self, filename, visited_tests):
        return self._create_all_x(filename, self.create_witness, visited_tests)

    def create_all_harnesses(self, filename, visited_tests):
        return self._create_all_x(filename, self.create_harness, visited_tests)
