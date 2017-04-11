import logging
import subprocess
import re
from abc import abstractmethod, ABCMeta

class InputGenerationError(Exception):

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

    @abstractmethod
    def _create_input_generation_cmds(self, filename):
        pass

    @abstractmethod
    def _get_sym_stmt(self, varname):
        pass

    @abstractmethod
    def replace_with_assume(self, assumption):
        pass

    @staticmethod
    def failed(result):
        return result.returncode < 0

    def generate_input(self, filename):
        cmds = self._create_input_generation_cmds(filename)
        for cmd in cmds:
            result = execute(cmd)
            if InputGenerator.failed(result):
                raise InputGenerationError('Generating input failed at command ' + ' '.join(cmd))

    def is_nondet_assignment(self, statement):
        is_nondet = "__VERIFIER_nondet_" in statement and '=' in statement
        if is_nondet:
            logging.info("Statement is nondet: %s", statement)
        return is_nondet

    def is_error(self, stmt):
        return stmt.strip() == "__VERIFIER_error()"

    def replace_nondet(self, statement):
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

    def error_reached(self, result):
        return result.returncode == error_return

    def _get_exit_stmt(self, return_code):
        return "exit(" + str(return_code) + ")"

    def replace_with_exit(self, code):
        return self._get_exit_stmt(code)


def execute(command, quiet=False, env=None):
    if not quiet:
        logging.info(" ".join(command))
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         universal_newlines=True,
                         env=env
                         )
    returncode = p.wait()
    output = p.stdout.read()
    err_output = p.stderr.read()
    return ExecutionResult(returncode, output, err_output)