import logging
import subprocess
import re
import os
import time
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

    def get_run_env(self):
        return os.environ

    @staticmethod
    def failed(result):
        return result.returncode < 0

    def generate_input(self, filename, stop_flag=None):
        cmds = self._create_input_generation_cmds(filename)
        for cmd in cmds:
            result = execute(cmd, env=self.get_run_env())
            if InputGenerator.failed(result):
                raise InputGenerationError('Generating input failed at command ' + ' '.join(cmd))

    def is_nondet_assignment(self, statement):
        is_nondet = "__VERIFIER_nondet_" in statement and '=' in statement
        if is_nondet:
            logging.info("Statement is nondet: %s", statement)
        return is_nondet

    def replace_verifier_assume(self, stmt):
        # __VERIFIER_assume(x) assumes that x is true. To model this, we replace it by 'if(!x) exit(0);'
        condition = '!' + stmt[stmt.find('('):stmt.rfind(')')+1]
        return self.get_conditional_exit_stmt(0, condition)

    def get_conditional_exit_stmt(self, return_code, condition):
        return "if(" + condition + ") exit(" + str(return_code) + ")"

    def _get_var_type(self, nondet_statement):
        return nondet_statement.split('_')[-1][:-2]  # split __VERIFIER_nondet_int() to int() and then to int

    def error_reached(self, result):
        return result.returncode == error_return

    def _get_exit_stmt(self, return_code):
        return "exit(" + str(return_code) + ")"

    def replace_with_exit(self, code):
        return self._get_exit_stmt(code)


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
