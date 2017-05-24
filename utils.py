import logging
import subprocess
import os
import time
import hashlib
import tempfile


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


error_return = 107
sv_benchmarks_dir = os.path.abspath('../sv-benchmarks/c')
spec_file = os.path.join(sv_benchmarks_dir, 'ReachSafety.prp')
output_dir = os.path.abspath('./output')
tmp = tempfile.mkdtemp()

if not os.path.exists(output_dir):
    os.mkdir(output_dir)


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


def get_env_with_path_added(path_addition):
    env = os.environ.copy()
    env['PATH'] = path_addition + os.pathsep + env['PATH']
    return env