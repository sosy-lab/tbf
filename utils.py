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

    def is_nondet_assume(self, statement):
        is_nondet = "__VERIFIER_nondet_" in statement and ('if' in statement or 'while' in statement)
        if is_nondet:
            logging.info("Statement is nondet: %s", statement)
        return is_nondet

    def is_error(self, stmt):
        return stmt.strip() == "__VERIFIER_error()"

    def replace_nondet_stmt(self, statement):
        split_statement = statement.split('=')
        if len(split_statement) <= 1:
            # TODO: handle __VERIFIER_nondet_X in while/if conditions
            return statement
        lhs = split_statement[0].strip()
        split_lhs = lhs.split()
        var_name = split_lhs[len(split_lhs) - 1]

        brace_re = re.compile('^\ *([}{]\ *)*')
        leading_braces = brace_re.match(lhs).group();
        lhs = lhs[len(leading_braces):]

        if lhs == var_name:
            declaration = ""
        else:
            declaration = lhs + ";"

        sym_stmt = self._get_sym_stmt(var_name)
        new_statement = [leading_braces, declaration, sym_stmt]

        return " ".join(new_statement)

    def replace_nondet_assume(self, statement):
        nondet_stmts = re.findall('__VERIFIER_nondet_.*?\)', statement)  # Regex .*? is non-greedy wildcard
        new_vars = list()
        modified_stmt = statement
        for ns in nondet_stmts:
            var_name = '__iuv' + str(self.var_counter)
            self.var_counter += 1
            var_type = self._get_var_type(ns)
            new_vars.append((var_name, var_type))
            modified_stmt = modified_stmt.replace(ns, var_name)

        new_stmts = list()
        for v in new_vars:
            new_stmts.append(v[1] + ' ' + v[0])
            new_stmts.append(self._get_sym_stmt(v[0]))
        new_stmts.append(modified_stmt)
        return ';\n'.join(new_stmts)

    def is_verifier_assume(self, stmt):
        return stmt.strip().startswith('__VERIFIER_assume(')

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


def execute(command, quiet=False, env=None, log_output=True, stop_flag=None):
    if not quiet:
        logging.info(" ".join(command))

    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT if log_output else subprocess.PIPE,
                         universal_newlines=True,
                         env=env
                         )

    returncode = p.poll()
    while returncode is None:
        if stop_flag and stop_flag.is_set():
            p.terminate()
            returncode = p.wait()
        else:
            time.sleep(0.001)
            returncode = p.poll()

    output, err_output = p.communicate()

    if log_output:
        logging.info(output)

    return ExecutionResult(returncode, output, err_output)


def flatten(list_of_lists):
    return [i for l in list_of_lists for i in l]
