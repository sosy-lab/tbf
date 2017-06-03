import logging
import subprocess
import os
import time
import hashlib
import tempfile
import pycparser
import re

parser = pycparser.CParser()
sym_var_prefix = '__sym_'


class ConfigError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


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


def execute(command, quiet=False, env=None, err_to_output=True, stop_flag=None, input_str=None):
    log_method = logging.debug if quiet else logging.info

    log_method(" ".join(command))

    p = subprocess.Popen(command,
                         stdin=subprocess.PIPE if input_str else None,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT if err_to_output else subprocess.PIPE,
                         universal_newlines=True,
                         env=env
                         )

    if stop_flag:
        returncode = p.poll()
        while returncode is None:
            if stop_flag.is_set():
                p.terminate()
                try:
                    returncode = p.wait(timeout=4)
                except subprocess.TimeoutExpired as e:
                    logging.info("Wasn't able to shut down process within timeout.")
            else:
                time.sleep(0.001)
                returncode = p.poll()
        output, err_output = p.communicate()
    else:
        output, err_output = p.communicate(input=input_str)
        returncode = p.poll()

    log_method(output)

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


def get_file_path(filename, temp_dir=True):
    if temp_dir:
        prefix = tmp
    else:
        prefix = output_dir
    return os.path.join(prefix, filename)


def get_file_name(filename):
    return os.path.basename(filename)


def get_env_with_path_added(path_addition):
    env = os.environ.copy()
    env['PATH'] = path_addition + os.pathsep + env['PATH']
    return env


def get_assume_method():
    return 'void __VERIFIER_assume(int cond) {\n    if(!cond) {\n        exit(0);\n    }\n}\n'


def get_method_head(method_name, method_type, param_types):
    method_head = '{0} {1}('.format(method_type, method_name)
    params = list()
    for (idx, pt) in enumerate(param_types):
        if '...' in pt:
            params.append('...')
        elif pt != 'void':
            params.append('{0} param{1}'.format(pt, idx))
    method_head += ', '.join(params)
    method_head += ')'
    return method_head


class Stopwatch(object):

    def __init__(self):
        self._intervals = list()
        self._current_start = None

    def start(self):
        assert not self._current_start
        self._current_start = time.perf_counter()  # We have to count sleep time because of other processes we wait on!

    def stop(self):
        end_time = time.perf_counter()
        assert self._current_start
        time_elapsed = self._process(end_time - self._current_start)
        self._current_start = None
        self._intervals.append(time_elapsed)

    def _process(self, value):
        return round(value, 3)

    def sum(self):
        val = sum(self._intervals) if self._intervals else 0
        return self._process(val)

    def avg(self):
        val = sum(self._intervals) / len(self._intervals) if len(self._intervals) else 0
        return self._process(val)

    def min(self):
        val = min(self._intervals) if self._intervals else 0
        return self._process(val)

    def max(self):
        val = max(self._intervals) if self._intervals else 0
        return self._process(val)

    def __str__(self):
        str_rep = "{0} (s)".format(self.sum())
        if len(self._intervals) > 1:
            str_rep += " (Avg.: {0} s, Min.: {1} s, Max.: {2} s)".format(self.avg(), self.min(), self.max())
        return str_rep


def parse_file_with_preprocessing(filename, includes=[]):
    preprocessed_filename = preprocess(filename, includes)
    ast = pycparser.parse_file(preprocessed_filename)
    return ast


def preprocess(filename, includes=[]):
    preprocessed_filename = '.'.join(filename.split('/')[-1].split('.')[:-1] + ['i'])
    preprocessed_filename = get_file_path(preprocessed_filename, temp_dir=True)
    if preprocessed_filename == filename:
        logging.warning("Overwriting existing file " + preprocessed_filename)

    # The defines (-D) remove gcc extensions that pycparser can't handle
    # -E : only preprocess
    # -o : output file name
    preprocess_cmd = ['gcc',
                      '-E',
                      '-D', '__attribute__(x)=',
                      '-D', '__extension=',
                      '-D', '__restrict=']
    for inc in includes:
        preprocess_cmd += ['-I', inc]
    preprocess_cmd += ['-o', preprocessed_filename,
                       filename]
    p = execute(preprocess_cmd)
    return preprocessed_filename


undefined_methods = None


def get_nondet_methods(file_content):
    global undefined_methods

    if undefined_methods is None:
        assert not os.path.exists(file_content)
        filename = get_file_path('temp.c', temp_dir=True)
        with open(filename, 'w+') as outp:
            outp.write(file_content)
        try:
            undefined_methods = find_undefined_methods(filename)
        except pycparser.plyparser.ParseError as e:
            logging.warning("Parse error in pycparser while parsing %s", filename)
            undefined_methods = find_nondet_methods(file_content)
    return undefined_methods


def find_undefined_methods(filename):
    import ast_visitor

    ast = parse_file_with_preprocessing(filename)

    func_decl_collector = ast_visitor.FuncDeclCollector()
    func_def_collector = ast_visitor.FuncDefCollector()

    func_decl_collector.visit(ast)
    function_declarations = func_decl_collector.func_decls
    func_def_collector.visit(ast)
    function_definitions = [f.name for f in func_def_collector.func_defs]
    function_definitions += ['__VERIFIER_assume', '__VERIFIER_error', 'malloc', 'memcpy']

    undef_func_prepared = [f for f in function_declarations if ast_visitor.get_name(f) not in function_definitions]
    undef_func_prepared = [_prettify(f) for f in undef_func_prepared]

    # List every undefined, but declared function only once.
    # This is necessary because there are a few SV-COMP programs that declare
    # functions multiple times.
    undef_func_names = set()
    undefined_functions = list()
    for f in undef_func_prepared:
        if f['name'] and f['name'] not in undef_func_names:
            undef_func_names.add(f['name'])
            undefined_functions.append(f)

    return undefined_functions


def find_nondet_methods(file_content):
    if os.path.exists(file_content):
        with open(file_content, 'r') as inp:
            content = inp.read()
    else:
        content = file_content
    method_names = set([s[:-2] for s in nondet_pattern.findall(content)])

    functions = list()
    for method_name in method_names:
        method_type = _get_return_type(method_name)
        functions.append({'name': method_name, 'type': method_type, 'params': []})
    return functions


def _get_return_type(method):
    assert method.startswith('__VERIFIER_nondet_')
    assert method[-2:] != '()'
    m_type = method[len('__VERIFIER_nondet_'):]
    if m_type == 'bool':
        m_type = '_Bool'
    elif m_type == 'u32':
        m_type = 'u32'
    elif m_type == 'unsigned':  # unsigned is a synonym for unsigned int, so recall the method with that
        m_type = 'unsigned int'
    elif m_type[0] == 'u':  # resolve uint to unsigned int (e.g.)
        m_type = 'unsigned ' + m_type[1:]
    elif m_type == 'pointer':
        m_type = 'void *'
    elif m_type == 'pchar':
        m_type = 'char *'
    return m_type


def _prettify(func_def):
    import ast_visitor
    name = ast_visitor.get_name(func_def)
    return_type = ast_visitor.get_type(func_def.type)
    params = list()
    if func_def.args:
        for parameter in func_def.args.params:
            param_type = ast_visitor.get_type(parameter)
            params.append(param_type)
    return {'name': name, 'type': return_type, 'params': params}


def get_sym_var_name(method_name):
    return sym_var_prefix + method_name


def get_corresponding_method_name(sym_var_name):
    return sym_var_name[len(sym_var_prefix):]


class Counter(object):

    def __init__(self):
        self._count = 0

    @property
    def count(self):
        return self._count

    def inc(self, amount=1):
        self._count += amount

    def __str__(self):
        return str(self.count)


class Constant(object):

    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return str(self.value)


class Statistics(object):

    def __init__(self, title):
        self._title = title
        self._stats = list()

    @property
    def title(self):
        return self._title

    def add_value(self, property, value):
        assert property not in [p for (p, v) in self._stats]
        self._stats.append((property, value))

    @property
    def stats(self):
        return self._stats

    def __str__(self):
        str_rep = '---- ' + self._title + ' ----\n'
        str_rep += '\n'.join([p + ': ' + str(v) for (p, v) in self._stats])
        return str_rep


class StatisticsPool(object):

    def __init__(self):
        self._stat_objects = list()

    @property
    def stats(self):
        return self._stat_objects

    def new(self, title):
        stat = Statistics(title)
        self._stat_objects.append(stat)
        return stat

    def __str__(self):
        return '\n\n'.join([str(s) for s in self._stat_objects])


error_return = 107
error_method = '__VERIFIER_error'
sv_benchmarks_dir = os.path.abspath('../sv-benchmarks/c')
spec_file = os.path.join(sv_benchmarks_dir, 'ReachSafety.prp')
output_dir = os.path.abspath('./output')
tmp = tempfile.mkdtemp()
nondet_pattern = re.compile('__VERIFIER_nondet_.+\(\)')

FALSE = 'false'
UNKNOWN = 'unknown'
TRUE = 'true'
ERROR = 'error'

statistics = StatisticsPool()

if not os.path.exists(output_dir):
    os.mkdir(output_dir)
