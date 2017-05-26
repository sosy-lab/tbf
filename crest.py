from input_generation import BaseInputGenerator
from test_validation import TestValidator
import utils
import os
import glob
import logging
from ast_visitor import NondetReplacer, NondetIdentifierCollector
from pycparser import c_ast as a
import pycparser
import re

bin_dir = os.path.abspath('./crest/bin')
lib_dir = os.path.abspath('./crest/lib')
include_dir = os.path.abspath('./crest/include')
name = 'crest'


class InputGenerator(BaseInputGenerator):

    def get_ast_replacer(self):
        return None

    def __init__(self, timelimit=0, log_verbose=False, search_heuristic='cfg', machine_model='32bit'):
        super().__init__(timelimit, machine_model)
        self.log_verbose = log_verbose

        self._run_env = utils.get_env_with_path_added(bin_dir)

        self.search_heuristic = search_heuristic
        self.num_iterations = 100

    def get_name(self):
        return name

    def get_run_env(self):
        return self._run_env

    def prepare(self, filecontent):
        content = '#include<crest.h>\n'
        content += filecontent
        content += '\n'
        nondet_methods_used = utils.get_nondet_methods(filecontent)
        for method in nondet_methods_used:  # append method definition at end of file content
            nondet_method_definition = self._get_nondet_method(method[:-2])
            content += nondet_method_definition
        return content

    def _get_nondet_method(self, method_name):
        assert method_name.startswith('__VERIFIER_nondet_')
        m_type = method_name[len('__VERIFIER_nondet_'):]
        if m_type[0] == 'u' and m_type != 'unsigned':  # resolve uint to unsigned int (e.g.)
            m_type = 'unsigned ' + m_type[1:]
        elif m_type == 'unsigned':  # unsigned is a synonym for unsigned int, so recall the method with that
            self._get_nondet_method('__VERIFIER_nondet_uint')
        if not self.is_supported_type(m_type):
            raise utils.InputGenerationError('Crest can\'t handle symbolic values of type ' + m_type)
        return self._create_nondet_method(method_name, m_type)

    def is_supported_type(self, method_type):
        return method_type in ['int', 'short', 'char', 'unsigned int', 'unsigned short', 'unsigned char']

    def _create_nondet_method(self, method_name, method_type):
        var_name = '__sym_' + method_name[len('__VERIFIER_nondet_'):]
        marker_method_call = 'CREST_' + '_'.join(method_type.split())
        return '{0} {1}() {{\n    {0} {2};\n ;\n    {3}({2});\n    return {2};\n}}\n'. \
            format(method_type, method_name, var_name, marker_method_call)

    def create_input_generation_cmds(self, filename):
        compile_cmd = [os.path.join(bin_dir, 'crestc'),
                       filename]
        # the output file name created by crestc is 'input file name - '.c'
        instrumented_file = filename[:-2]
        input_gen_cmd = [os.path.join(bin_dir, 'run_crest'),
                         instrumented_file,
                         str(self.num_iterations),
                         '-' + self.search_heuristic]
        return [compile_cmd, input_gen_cmd]


class AstReplacer(NondetReplacer):

    def __init__(self):
        super().__init__()
        self.parser = pycparser.CParser()

    def get_marker_function(self, var_type):
        type_name = var_type.type.names[0]
        if type_name == 'int':
            return 'CREST_int'
        elif type_name == 'short':
            return 'CREST_short'
        elif type_name == 'char':
            return 'CREST_char'
        elif type_name == 'unsigned int':
            return 'CREST_unsigned_int'
        elif type_name == 'unsigned short':
            return 'CREST_unsigned_short'
        elif type_name == 'unsigned_char':
            return 'CREST_unsigned_char'
        else:
            # raise AssertionError("Unhandled var type: ", var_type)
            return 'CREST_int'

    # Hook
    def get_nondet_marker(self, var_name, var_type):
        function_name = self.get_marker_function(var_type)
        parameters = [a.ID(var_name)]
        return a.FuncCall(a.ID(function_name), a.ExprList(parameters))

    # Hook
    def get_error_stmt(self):
        parameters = [a.Constant('int', str(utils.error_return))]
        return a.FuncCall(a.ID('exit'), a.ExprList(parameters))

    # Hook
    def get_preamble(self):
        return []


class CrestTestValidator(TestValidator):

    def __init__(self, machine_model='32bit'):
        super().__init__(machine_model)
        self.counter = 0

    def get_name(self):
        return name

    def get_test_vector(self, test):
        test_vector = dict()
        with open(test, 'r') as inp:
            for line in inp.readlines():
                try:
                    test_vector[self.counter] = {'name': None, 'value': line.strip()}
                    self.counter += 1
                except ValueError as e:
                    raise AssertionError(e)
        if not test_vector:
            return None
        else:
            return test_vector

    def create_witness(self, filename, test_file):
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
        test_vector = self.get_test_vector(test_file)
        # If no inputs are defined don't create a witness
        if not test_vector:
            logging.debug("Test case empty, no witness is created")
            return None
        witness = self.witness_creator.create_witness(producer=self.get_name(),
                                                      filename=filename,
                                                      test_vector=test_vector,
                                                      nondet_methods=utils.get_nondet_methods(filename),
                                                      machine_model=self.machine_model,
                                                      error_line=self.get_error_line(filename))

        test_name = os.path.basename(test_file)
        witness_file = test_name + ".witness.graphml"
        witness_file = utils.get_file_path(witness_file, temp_dir=False)

        return {'name': witness_file, 'content': witness}

    def create_all_witnesses(self, filename):
        witnesses = []
        test_name_pattern = re.compile('input[0-9]+')
        for test_file in [f for f in os.listdir('.') if test_name_pattern.match(f)]:
            new_witness = self.create_witness(filename, test_file)
            if new_witness:  # It's possible that no witness is created due to a missing test vector
                witnesses.append(new_witness)
        return witnesses