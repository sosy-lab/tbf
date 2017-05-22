import logging
import subprocess
import os
import time
import hashlib
import tempfile
import pycparser
from pycparser import c_generator
from abc import abstractmethod, ABCMeta

class InputGenerationError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


class ParseError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


class CompileError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


class ExecutionResult(object):
    """Results of a subprocess execution."""

    def __init__(self, returncode, stdout, stderr):
        self._returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    @property
    def returncode(self):
        return self._returncode

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr


error_return = 117


class InputGenerator(object):
    __metaclass__ = ABCMeta

    var_counter = 0

    @abstractmethod
    def _create_input_generation_cmds(self, filename):
        pass

    @abstractmethod
    def _get_sym_stmt(self, varname):
        pass

    @abstractmethod
    def replace_with_assume(self, assumption):
        pass

    @abstractmethod
    def get_ast_replacer(self):
        return None

    @abstractmethod
    def get_name(self):
        return None

    @abstractmethod
    def get_run_env(self):
        return os.environ

    @abstractmethod
    def create_nondet_var_map(self, filename):
        pass

    @staticmethod
    def failed(result):
        return result.returncode < 0

    def __init__(self, timelimit, machine_model):
        self._nondet_var_map = None
        self.machine_model = machine_model
        self.timelimit = int(timelimit) if timelimit else 0
        self.tmp = tempfile.mkdtemp()

    def _create_file_path(self, filename):
        return os.path.join(self.tmp, filename)

    def prepare(self, filename):
        """
        Prepares the file with the given name according to the module
        provided. E.g., if the module provided is intended to prepare for klee,
        the file provided will be prepared to run klee on it.
        The prepared file is written to a new file. The name of this file is
        returned by this function.

        :param filename: The name of the file to prepare
        :param module: The module to use for preparation
        :return: The name of the file containing the prepared content
        """
        suffix = filename.split('.')[-1]
        name_new_file = '.'.join(os.path.basename(filename).split('.')[:-1] + [self.get_name(), suffix])
        name_new_file = self._create_file_path(name_new_file)
        if os.path.exists(name_new_file):
            logging.warning("Prepared file already exists. Not preparing again.")
            return name_new_file

        else:
            ast = self.parse_file(filename)
            r = self.get_ast_replacer()
            # ps is list of ast pieces that must still be appended (must be empty!), new_ast is the modified ast
            ps, new_ast = r.visit(ast)
            assert not ps  # Make sure that there are no ast pieces left that must be appended
            logging.debug("Prepared content")
            logging.debug("Writing to file %s", name_new_file)
            generator = c_generator.CGenerator()
            with open(name_new_file, 'w+') as new_file:
                new_file.write(generator.visit(new_ast))

            return name_new_file

    def parse_file(self, filename):
        with open(filename, 'r') as i:
            content = i.readlines()
        # Remove gcc extensions that pycparser can't handle
        content.insert(0, '#define __attribute__(x)\n')
        content.insert(1, '#define __extension__\n')
        content = ''.join(content)
        preprocessed_filename = '.'.join(filename.split('.')[:-1] + ['i'])
        preprocessed_filename = self._create_file_path(preprocessed_filename)
        if preprocessed_filename == filename:
            logging.info("File already preprocessed")
        else:
            preprocess_cmd = ['gcc', '-E', '-D', '__attribute__(x)=', '-D', '__extension=', '-o', preprocessed_filename, filename]
            p = execute(preprocess_cmd, input_str=content)

        ast = pycparser.parse_file(preprocessed_filename)
        return ast

    def get_nondet_var_map(self, filename):
        """
        Returns data structure with information about all non-deterministic variables.
        Expected structure: var_map[variable_name] = {'line': line_number, 'origin file': source file,}
        """
        if not self._nondet_var_map:
            self._nondet_var_map = self.create_nondet_var_map(filename)
        return self._nondet_var_map

    def generate_input(self, filename, stop_flag=None):
        file_for_analysis = self.prepare(filename)
        cmds = self._create_input_generation_cmds(file_for_analysis)
        for cmd in cmds:
            result = execute(cmd, env=self.get_run_env())
            if InputGenerator.failed(result):
                raise InputGenerationError('Generating input failed at command ' + ' '.join(cmd))

    def check_inputs(self, filename, generator_thread=None):
        prepared_file = self.prepare(filename)
        produced_witnesses = self.create_all_witnesses(prepared_file)

        for witness in produced_witnesses:
            with open(witness['name'], 'w+') as outp:
                outp.write(witness['content'])

def execute_in_container(command):
    cmd = ['runexec'] + command
    return execute(cmd)

def execute(command, quiet=False, env=None, log_output=True, stop_flag=None, input_str=None):
    if not quiet:
        logging.info(" ".join(command))

    p = subprocess.Popen(command,
                         stdin=subprocess.PIPE if input_str else None,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT if log_output else subprocess.PIPE,
                         universal_newlines=True,
                         env=env
                         )

    if stop_flag:
        returncode = p.poll()
        while returncode is None:
            if stop_flag.is_set():
                p.terminate()
                returncode = p.wait()
            else:
                time.sleep(0.001)
                returncode = p.poll()
        output, err_output = p.communicate()
    else:
        output, err_output = p.communicate(input=input_str)
        returncode = p.poll()

    if log_output:
        logging.info(output)

    return ExecutionResult(returncode, output, err_output)


def flatten(list_of_lists):
    return [i for l in list_of_lists for i in l]


def get_hash(filename):
    buf_size = 65536
    sha1 = hashlib.sha1()

    with open(filename, 'rb') as inp:
        data = inp.read(buf_size)
        while data:
            sha1.update(data)
            data = inp.read(buf_size)

    return sha1.hexdigest()


def error_reached(result):
    return result.returncode == error_return
