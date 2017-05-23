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
sv_benchmarks_dir = os.path.abspath('../sv-benchmarks/c')
spec_file = os.path.join(sv_benchmarks_dir, 'ReachSafety.prp')
output_dir = os.path.abspath('./output')
tmp = tempfile.mkdtemp()

if not os.path.exists(output_dir):
    os.mkdir(output_dir)

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

    @abstractmethod
    def create_all_witnesses(self, filename):
        return None

    @staticmethod
    def failed(result):
        return result.returncode < 0

    def __init__(self, timelimit, machine_model):
        self._nondet_var_map = None
        self.machine_model = machine_model
        self.timelimit = int(timelimit) if timelimit else 0

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
        name_new_file = create_file_path(name_new_file, temp_dir=True)
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
        preprocessed_filename = '.'.join(filename.split('/')[-1].split('.')[:-1] + ['i'])
        preprocessed_filename = create_file_path(preprocessed_filename, temp_dir=True)
        if preprocessed_filename == filename:
            logging.info("File already preprocessed")
        else:
            # The defines (-D) remove gcc extensions that pycparser can't handle
            # -E : only preprocess
            # -o : output file name
            preprocess_cmd = ['gcc',
                              '-E',
                              '-D', '__attribute__(x)=',
                              '-D', '__extension=',
                              '-o', preprocessed_filename,
                              filename]
            p = execute(preprocess_cmd)

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

        validator = ValidationRunner()

        for witness in produced_witnesses:
            witness_name = witness['name']
            with open(witness_name, 'w+') as outp:
                outp.write(witness['content'])

            results = validator.run(filename, witness_name)

            logging.info('Results for %s: %s', witness_name, str(results))
            if [s for s in results if 'false' in s]:
                return True
        return False


class ValidationRunner(object):

    def __init__(self):
        self.validators = [FShellW2t()]

    def run(self, program_file, witness_file):
        results = []
        for validator in self.validators:
            result = validator.validate(program_file, witness_file)
            results.append(result)

        return results


class Validator(object):

    __metaclass__ = ABCMeta

    def __init__(self, tool_name):
        self.tool = import_tool(tool_name)
        self.executable = self.tool.executable()

    def validate(self, program_file, witness_file):
        cmd_result = execute(self._get_cmd(program_file, witness_file))

        validation_result = self.tool.determine_result(cmd_result.returncode, None, cmd_result.stdout, isTimeout=False)
        return validation_result

    @abstractmethod
    def _get_cmd(self, program_file, witness_file):
        pass


class CPAcheckerValidator(object):

    def __init__(self):
        self.tool = import_tool('cpachecker')
        self.executable = self.tool.executable()

    def _get_cmd(self, program_file, witness_file):
        return [self.executable] +\
               get_cpachecker_options(witness_file) +\
               ['-witnessValidation', program_file]


class UAutomizerValidator(Validator):

    def __init__(self):
        super().__init__('ultimateautomizer')

    def _get_cmd(self, program_file, witness_file):
        machine_model = get_machine_model(witness_file)
        if '32' in machine_model:
            machine_model = '32bit'
        elif '64' in machine_model:
            machine_model = '64bit'
        else:
            raise AssertionError("Unhandled machine model: " + machine_model)

        cmd = [self.executable,
               '--spec', spec_file,
               '--validate', witness_file,
               '--file', program_file,
               machine_model]
        return cmd


class CpaW2t(Validator):

    def __init__(self):
        super().__init__('cpa-witness2test')

    def _get_cmd(self, program_file, witness_file):
        return [self.executable] +\
               get_cpachecker_options(witness_file) +\
               ['-witness2test', program_file]


class FShellW2t(Validator):

    def __init__(self):
        super().__init__('witness2test')

    def _get_cmd(self, program_file, witness_file):
        machine_model = get_machine_model(witness_file)
        if '32' in machine_model:
            machine_model = '-m32'
        elif '64' in machine_model:
            machine_model = '-m64'
        else:
            raise AssertionError('Unhandled machine model: ' + machine_model)

        return [self.executable,
                '--propertyfile', spec_file,
                '--graphml-witness', witness_file,
                machine_model,
                program_file]


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


def get_machine_model(witness_file):
    with open(witness_file, 'r') as inp:
        for line in inp.readlines():
            if 'architecture' in line:
                if '32' in line:
                    return '32bit'
                elif '64' in line:
                    return '64bit'
                else:
                    raise AssertionError('Unknown architecture in witness line: ' + line)


def import_tool(tool_name):
    if '.' in tool_name:
        tool_module = tool_name
    else:
        tool_module = 'benchexec.tools.' + tool_name
    return __import__(tool_module, fromlist=['Tool']).Tool()

def get_cpachecker_options(witness_file):
    machine_model = get_machine_model(witness_file)
    if '32' in machine_model:
        machine_model = '-32'
    elif '64' in machine_model:
        machine_model = '-64'
    else:
        raise AssertionError('Unknown machine model: ' + machine_model)

    return [
    '-setprop', 'witness.checkProgramHash=false',
    '-disable-java-assertions',
    '-heap', '4000M',
    '-setprop', 'cfa.simplifyCfa=false',
    '-setprop', 'cfa.allowBranchSwapping=false',
    '-setprop', 'cpa.predicate.ignoreIrrelevantVariables=false',
    '-setprop', 'cpa.predicate.refinement.performINitialStaticRefinement=false',
    '-setprop', 'counterexample.export.compressWitness=false',
    '-setprop', 'counterexample.export.assumptions.includeConstantsForPointers=false',
    '-setprop', 'analysis.summaryEdge=true',
    '-setprop', 'cpa.callstack.skipVoidRecursion=true',
    '-setprop', 'cpa.callstack.skipFunctionPointerRecursion=true',
    '-setprop', 'cpa.predicate.memoryAllocationsAlwaysSucceed=true',
    '-witness', witness_file,
    machine_model,
    '-spec', spec_file]


def create_file_path(filename, temp_dir=True):
    if temp_dir:
        prefix = tmp
    else:
        prefix = output_dir
    return os.path.join(prefix, filename)