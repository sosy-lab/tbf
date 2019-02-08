import logging
import subprocess
import os
import hashlib
import tempfile
import pycparser
import re
from struct import unpack
import codecs
import shutil

from math import floor

import threading
import time


class MachineModel(object):

    def __init__(self, wordsize, name, short_size, int_size, long_size,
                 long_long_size, float_size, double_size, long_double_size,
                 compile_param):
        assert wordsize == 32 or wordsize == 64
        self._wordsize = wordsize
        self._name = name
        self.model = {
            'short': short_size,
            'int': int_size,
            'long': long_size,
            'long long': long_long_size,
            'float': float_size,
            'double': double_size,
            'long double': long_double_size
        }
        self._compile_param = compile_param

    @property
    def short_size(self):
        return self.model['short']

    @property
    def int_size(self):
        return self.model['int']

    @property
    def long_size(self):
        return self.model['long']

    @property
    def long_long_size(self):
        return self.model['long long']

    @property
    def float_size(self):
        return self.model['float']

    @property
    def double_size(self):
        return self.model['double']

    @property
    def long_double_size(self):
        return self.model['long double']

    @property
    def compile_parameter(self):
        return self._compile_param

    @property
    def is_64(self):
        return self._wordsize == 64

    @property
    def is_32(self):
        return self._wordsize == 32

    @property
    def name(self):
        return self._name

    def get_size(self, data_type):
        if 'short' in data_type:
            return self.short_size
        elif 'long long' in data_type:
            return self.long_long_size
        elif 'long double' in data_type:
            return self.long_double_size
        elif 'long' in data_type:
            return self.long_size
        elif 'double' in data_type:
            return self.double_size
        elif 'float' in data_type:
            return self.float_size
        elif 'int' in data_type:
            return self.int_size
        else:
            raise AssertionError("Unhandled data type: " + data_type)

    def __str__(self):
        return "%sbit" % self._wordsize


class TestCase(object):

    def __init__(self, name, origin_file, content):
        self._name = name
        self._origin = os.path.abspath(origin_file)
        self._content = content

    @property
    def name(self):
        return self._name

    @property
    def origin(self):
        return self._origin

    @property
    def content(self):
        return self._content

    def __str__(self):
        return self.name + "(" + self.origin + ")"


class TestVector(object):
    """Test vector.

    Consists of a unique name, the original file that
    describes the test vector,
    and the vector as a sequence of test inputs.
    Each test input is a dictionary and consists
    of a 'value' and a 'name'.
    """

    def __init__(self, name, origin_file):
        self.name = name
        self.origin = origin_file
        self._vector = list()

    def add(self, value, method=None):
        self._vector.append({'value': value, 'name': method})

    @property
    def vector(self):
        """The sequence of test inputs of this test vector.

        Each element of this sequence is a dict
        and consists of two entries: 'value' and 'name'.
        The 'value' entry describes the input value, as it should be given
        to the program as input.
        The 'name' entry describes the program input method
        through which the value is retrieved. The value of this entry may be None.
        """
        return self._vector

    def __len__(self):
        return len(self.vector)

    def __str__(self):
        return self.origin + " (" + str(self.vector) + " )"


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


class Verdict(object):
    """Results of a test validation, test execution or klee-replay currently."""

    def __init__(self, verdict, test=None, test_vector=None, harness=None):
        self.verdict = verdict
        self.test = test
        self.test_vector = test_vector
        self.harness = harness

    def is_positive(self):
        """
        Returns whether the verdict is positive, i.e., whether a target was found.
        :return: true if the verdict represents that a target was found, false otherwise
        """
        return self.verdict == FALSE

    def __str__(self):
        return self.verdict


class VerdictTrue(Verdict):

    def __init__(self):
        super().__init__(TRUE)


class VerdictFalse(Verdict):

    def __init__(self, test_origin, test_vector=None, harness=None):
        super().__init__(FALSE, test_origin, test_vector, harness)


class VerdictUnknown(Verdict):

    def __init__(self):
        super().__init__(UNKNOWN)


def set_stop_timer(timelimit, stop_event):
    timewatcher = threading.Timer(timelimit, stop_event.set)
    timewatcher.start()


def execute(command,
            quiet=False,
            env=None,
            err_to_output=True,
            stop_flag=None,
            input_str=None,
            timelimit=None,
            show_output=False):

    def wait_and_terminate(timelimit, stop_flag, process):
        def shut_down(process):
            process.kill()
            returncode = process.wait()

            return returncode

        if timelimit:
            stopwatch = Stopwatch()
            stopwatch.start()

        returncode = process.poll()
        while returncode is None:
            if (stop_flag and stop_flag.is_set()) \
                    or (timelimit and stopwatch.curr_s() > timelimit):
                logging.info("Timeout of %ss expired or told to stop. Killing process.", timelimit if timelimit else "- ")
                returncode = shut_down(process)
            else:
                time.sleep(0.001)
                returncode = process.poll()

    log_cmd = logging.debug if quiet else logging.info

    if env:
        logging.debug("PATH=%s", env['PATH'])
        logging.debug(
            "LD_LIBRARY_PATH=%s",
            env['LD_LIBRARY_PATH'] if 'LD_LIBRARY_PATH' in env else "[]")
    log_cmd(" ".join(command))

    p = subprocess.Popen(
        command,
        stdin=subprocess.PIPE if input_str else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if err_to_output else subprocess.PIPE,
        universal_newlines=False,
        env=env)

    waiter = threading.Thread(target=wait_and_terminate, args=(timelimit, stop_flag, p))
    waiter.start()
    if input_str and type(input_str) is not bytes:
        input_str = input_str.encode()
    output, err_output = p.communicate(input=input_str)
    returncode = p.poll()

    try:
        output = output.decode() if output else ''
    except UnicodeDecodeError:
        pass
    try:
        err_output = err_output.decode()  if err_output else ''
    except UnicodeDecodeError:
        pass
    log_output = logging.info if show_output else logging.debug
    if output:
        log_output(output)
    if err_output:
        log_output(err_output)

    return ExecutionResult(returncode, output, err_output)


def get_executable(exec):
    """
    Returns the full path to the given executable.
    If the executable does not exist, None is returned.
    """
    return shutil.which(exec)


def get_output_path(filename):
    return os.path.join(OUTPUT_DIR, filename)


def create_temp():
    return tempfile.mkdtemp(prefix='tbf_')


def get_env():
    return os.environ.copy()


def add_ld_path_to_env(env, lib_dir):
    new_ld_path = [str(lib_dir)]
    if 'LD_LIBRARY_PATH' in env:
        if type(env['LD_LIBRARY_PATH']) is list:
            new_ld_path = new_ld_path + env['LD_LIBRARY_PATH']
        else:
            new_ld_path = new_ld_path + [env['LD_LIBRARY_PATH']]
    new_env = env.copy()
    new_env['LD_LIBRARY_PATH'] = ':'.join(new_ld_path)
    return new_env


def get_env_with_path_added(path_addition):
    env = os.environ.copy()
    env['PATH'] = path_addition + os.pathsep + env['PATH']
    return env


def get_assume_method():
    return 'void __VERIFIER_assume(int cond) {\n    if(!cond) {\n        abort();\n    }\n}\n'


def get_error_method_definition(error_method):
    return 'void ' + error_method + '() {{ fprintf(stderr, \"{0}\\n\"); exit(1); }}\n'.format(
        ERROR_STRING)


def get_method_head(method_name, method_type, param_types):
    method_head = '{0} {1}('.format(method_type, method_name)
    params = list()
    for (idx, pt) in enumerate(param_types):
        if '...' in pt:
            params.append('...')
        elif pt != 'void':
            if '{}' not in pt:
                pt += " {}"
            params.append(pt.format("param{}".format(idx)))
        elif params:
            raise AssertionError("Void type parameter in method " + method_name)
    method_head += ', '.join(params)
    method_head += ')'
    return method_head


class Stopwatch(object):

    def __init__(self):
        self._intervals = list()
        self._current_start = None

    def start(self):
        assert not self._current_start
        # We have to count sleep time because of other processes we wait on!
        self._current_start = time.perf_counter()

    def stop(self):
        end_time = time.perf_counter()
        assert self._current_start
        time_elapsed = self._process(end_time - self._current_start)
        self._current_start = None
        self._intervals.append(time_elapsed)

    def is_running(self):
        return self._current_start is not None

    def curr_s(self):
        """ Return current time in seconds """
        assert self._current_start
        return int(
            floor(self._process(time.perf_counter() - self._current_start)))

    def _process(self, value):
        return round(value, 3)

    def sum(self):
        val = sum(self._intervals) if self._intervals else 0
        return self._process(val)

    def avg(self):
        val = sum(self._intervals) / len(self._intervals) if len(
            self._intervals) else 0
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
            str_rep += " (Avg.: {0} s, Min.: {1} s, Max.: {2} s)".format(
                self.avg(), self.min(), self.max())
        return str_rep


def _rewrite_cproblems(content):
    need_struct_body = False
    skip_asm = False
    in_attribute = False
    in_cxx_comment = False
    prepared_content = ''
    for line in [c + "\n" for c in content.split('\n')]:
        # remove C++-style comments
        if in_cxx_comment:
            if re.search(r'\*/', line):
                line = re.sub(r'.*\*/', '', line)
                in_cxx_comment = False
            else:
                line = ''
        else:
            line = re.sub(r'/\*.*?\*/', '', line)
        if re.search(r'/\*', line):
            line = re.sub(r'/\*.*', '', line)
            in_cxx_comment = True
        # remove __attribute__
        line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\)\)\s*', '', line)
        # line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\(\s*[a-zA-Z0-9_, "\.]+\s*\)\s*\)\)\s*', '', line)
        # line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\(\s*sizeof\s*\([a-z ]+\)\s*\)\s*\)\)\s*', '', line)
        # line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\(\s*\([0-9]+\)\s*<<\s*\([0-9]+\)\s*\)\s*\)\)\s*', '', line)
        line = re.sub(r'__attribute__\s*\(\(.*\)\)\s*', '', line)
        if re.search(r'__attribute__\s*\(\(', line):
            line = re.sub(r'__attribute__\s*\(\(.*', '', line)
            in_attribute = True
        elif in_attribute:
            line = re.sub(r'.*\)\)', '', line)
            in_attribute = False
        # rewrite some GCC extensions
        line = re.sub(r'__extension__', '', line)
        line = re.sub(r'__restrict', '', line)
        line = re.sub(r'__restrict__', '', line)
        line = re.sub(r'__inline__', '', line)
        line = re.sub(r'__inline', '', line)
        line = re.sub(r'__const', 'const', line)
        line = re.sub(r'__signed__', 'signed', line)
        line = re.sub(r'__builtin_va_list', 'int', line)
        # a hack for some C-standards violating code in LDV benchmarks
        if need_struct_body and re.match(r'^\s*}\s*;\s*$', line):
            line = 'int __dummy; ' + line
            need_struct_body = False
        elif need_struct_body:
            need_struct_body = re.match(r'^\s*$', line) is not None
        elif re.match(r'^\s*struct\s+[a-zA-Z0-9_]+\s*{\s*$', line):
            need_struct_body = True
        # remove inline asm
        if re.match(r'^\s*__asm__(\s+volatile)?\s*\("([^"]|\\")*"[^;]*$', line):
            skip_asm = True
        elif skip_asm and re.search(r'\)\s*;\s*$', line):
            skip_asm = False
            line = '\n'
        if (skip_asm or re.match(
                r'^\s*__asm__(\s+volatile)?\s*\("([^"]|\\")*"[^;]*\)\s*;\s*$',
                line)):
            line = '\n'
        # remove asm renaming
        line = re.sub(r'__asm__\s*\(""\s+"[a-zA-Z0-9_]+"\)', '', line)
        prepared_content += line
    return prepared_content


def parse_file_with_preprocessing(file_content, machine_model, includes=()):
    preprocessed_content = preprocess(file_content, machine_model, includes)
    preprocessed_content = _rewrite_cproblems(preprocessed_content)
    parser = pycparser.CParser()
    ast = parser.parse(preprocessed_content)
    return ast


def preprocess(file_content, machine_model, includes=()):
    mm_arg = machine_model.compile_parameter

    # -E : only preprocess
    # -o : output file name
    # -xc : Use C language
    # - : Read code from stdin
    preprocess_cmd = ['gcc', '-E', '-xc', mm_arg]
    for inc in includes:
        preprocess_cmd += ['-I', inc]
    final_cmd = preprocess_cmd + ['-std=gnu11', '-lm', '-']
    p = execute(
        final_cmd, err_to_output=False, input_str=file_content, quiet=False)
    if p.returncode != 0:
        final_cmd = preprocess_cmd + ['-std=gnu90', '-lm', '-']
        p = execute(
            final_cmd, err_to_output=False, input_str=file_content, quiet=False)
    return p.stdout


def find_nondet_methods(filename, svcomp_only, excludes=None):
    logging.debug("Finding undefined methods")
    with open(filename, 'r') as inp:
        file_content = inp.read()
    if not svcomp_only:
        try:
            undefined_methods = _find_undefined_methods(file_content, excludes)
        except pycparser.plyparser.ParseError as e:
            logging.warning("Parse failure with pycparser while parsing: %s", e)
            undefined_methods = _find_nondet_methods(file_content, excludes)
    else:
        undefined_methods = _find_nondet_methods(file_content, excludes)
    logging.debug("Undefined methods: %s", undefined_methods)
    return undefined_methods


def _find_undefined_methods(file_content, excludes):
    import tbf.ast_visitor as ast_visitor

    ast = parse_file_with_preprocessing(file_content, MACHINE_MODEL_32)

    func_decl_collector = ast_visitor.FuncDeclCollector()
    func_def_collector = ast_visitor.FuncDefCollector()

    func_decl_collector.visit(ast)
    function_declarations = func_decl_collector.func_decls
    func_def_collector.visit(ast)
    function_definitions = [f.name for f in func_def_collector.func_defs]
    function_definitions += IMPLICIT_FUNCTIONS

    if excludes:
        function_definitions += excludes

    undef_func_prepared = [
        f for f in function_declarations
        if ast_visitor.get_name(f) not in function_definitions
    ]
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


def _find_nondet_methods(file_content, excludes):
    if os.path.exists(file_content):
        with open(file_content, 'r') as inp:
            content = inp.read()
    else:
        content = file_content
    nondet_pattern = re.compile('__VERIFIER_nondet_.+?\(\)')
    method_names = set([
        s[:-2]
        for s in nondet_pattern.findall(content)
        if s[:-2] not in excludes
    ])

    functions = list()
    for method_name in method_names:
        method_type = _get_return_type(method_name)
        functions.append({
            'name': method_name,
            'type': method_type,
            'params': []
        })
    svcomp_error_name = '__VERIFIER_error'
    if svcomp_error_name not in excludes:
        functions.append({'name': '__VERIFIER_error', 'type': 'void', 'params': []})
    return functions


def _get_return_type(verifier_nondet_method):
    assert verifier_nondet_method.startswith('__VERIFIER_nondet_')
    assert verifier_nondet_method[-2:] != '()'
    m_type = verifier_nondet_method[len('__VERIFIER_nondet_'):].lower()
    if m_type == 'bool':
        m_type = '_Bool'
    elif m_type == 'u32':
        m_type = 'unsigned int'
    elif m_type == 'u16':
        m_type = 'unsigned short'
    elif m_type == 'u8':
        m_type = 'unsigned char'
    elif m_type == 'unsigned':  # unsigned is a synonym for unsigned int, so recall the method with that
        m_type = 'unsigned int'
    elif m_type[0] == 'u':  # resolve uint to unsigned int (e.g.)
        m_type = 'unsigned ' + m_type[1:]
    elif m_type == 'pointer':
        m_type = 'void *'
    elif m_type == 'pchar':
        m_type = 'char *'
    elif m_type == 's8':
        m_type = 'char'
    return m_type


def _prettify(func_def):
    import tbf.ast_visitor as ast_visitor
    name = ast_visitor.get_name(func_def)
    return_type = ast_visitor.get_type(func_def.type)
    params = list()
    if func_def.args:
        for parameter in func_def.args.params:
            param_type = ast_visitor.get_type(parameter)
            params.append(param_type)
    return {'name': name, 'type': return_type, 'params': params}


def get_sym_var_name(method_name):
    name = SYM_VAR_PREFIX + method_name
    logging.debug("Getting sym var name for method %s: %s", method_name, name)
    return name


def get_corresponding_method_name(sym_var_name):
    name = sym_var_name[len(SYM_VAR_PREFIX):]
    logging.debug("Getting method name for %s: %s", sym_var_name, name)
    return name


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


def found_err(run_result):
    if isinstance(run_result.stderr, bytes):
        err_out = run_result.stderr.decode()
    else:
        err_out = run_result.stderr
    return run_result.stderr and ERROR_STRING in err_out


def get_prepared_name(filename, tool_name):
    return '.'.join(
        os.path.basename(filename).split('.')[:-1] + [tool_name, 'c'])


def provide_directory(directory):
    if os.path.exists(directory):
        # despite the name, ignore_errors=True allows removal of non-empty directories
        shutil.rmtree(directory, ignore_errors=True)
    os.mkdir(directory)
    return directory


def get_error_spec(error_method):
    return "COVER(init(main()), FQL(COVER EDGES( @ CALL(%s))) )" % error_method


def get_coverage_spec():
    return "COVER( init(main()), FQL(COVER EDGES(@BASICBLOCKENTRY)) )"


SYM_VAR_PREFIX = '__sym_'

ERROR_STRING = "Error found."
OUTPUT_DIR = os.path.abspath('./output')

FALSE = 'FALSE'
UNKNOWN = 'UNKNOWN'
TRUE = 'TRUE'
ERROR = 'ERROR'
DONE = 'DONE'

MACHINE_MODEL_32 = MachineModel(32, "32 bit linux", 2, 4, 4, 8, 4, 8, 12,
                                '-m32')
MACHINE_MODEL_64 = MachineModel(64, "64 bit linux", 2, 4, 8, 8, 4, 8, 16,
                                '-m64')

if not os.path.exists(OUTPUT_DIR):
    os.mkdir(OUTPUT_DIR)

EXTERNAL_DECLARATIONS = """
struct _IO_FILE;
typedef struct _IO_FILE FILE;
extern struct _IO_FILE *stdin;
extern struct _IO_FILE *stderr;
typedef long unsigned int size_t;
extern void abort (void) __attribute__ ((__nothrow__ , __leaf__))
    __attribute__ ((__noreturn__));
extern void exit (int __status) __attribute__ ((__nothrow__ , __leaf__))
     __attribute__ ((__noreturn__));
extern char *fgets (char *__restrict __s, int __n, FILE *__restrict __stream);
extern int sscanf (const char *__restrict __s,
    const char *__restrict __format, ...) __attribute__ ((__nothrow__ , __leaf__));
extern size_t strlen (const char *__s)
    __attribute__ ((__nothrow__ , __leaf__))
    __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));
extern int fprintf (FILE *__restrict __stream,
    const char *__restrict __format, ...);
extern void *malloc (size_t __size) __attribute__ ((__nothrow__ , __leaf__))
    __attribute__ ((__malloc__));
extern void *memcpy (void *__restrict __dest, const void *__restrict __src,
    size_t __n) __attribute__ ((__nothrow__ , __leaf__)) __attribute__ ((__nonnull__ (1, 2)));

"""

GCC_BUILTINS = [
    'cos',
    'sin',
    'tan',
    'acos',
    'asin',
    'atan',
    'atan2',
    'cosh',
    'sinh',
    'tanh',
    'acosh',
    'asinh',
    'atanh',
    'exp',
    'frexp',
    'ldexp',
    'log',
    'log10',
    'modf',
    'exp2',
    'expm1',
    'iologb',
    'log1p',
    'log2',
    'logb',
    'scalbn',
    'scalbln',
    'pow',
    'sqrt',
    'cbrt',
    'hypot',
    'erf',
    'erfc',
    'tgamma',
    'lgamma',
    'ceil',
    'floor',
    'fmod',
    'trunc',
    'round',
    'lround',
    'llround',
    'rint',
    'lrint',
    'nearbyint',
    'remainder',
    'remquo',
    'copysing',
    'nan',
    'nanf',
    'nanl',
    'nextafter',
    'nettoward',
    'fdim',
    'fmax',
    'fmal',
    'fmin',
    'fabs',
    'abs',
    'fma',
    'fpclassify',
    'fpclassifyf',
    'fpclassifyl',
    'isfinite',
    'isfinitef',
    'isfinitel',
    'finite',
    'finitef',
    'finitel',
    'isinf',
    'isinff',
    'isinfl',
    'isnan',
    'isnanf',
    'isnanl',
    'isnormal',
    'signbit',
    'signbitf',
    'signbitl',
    'isgreater',
    'isgreaterequal',
    'isless',
    'islessequal',
    'islessgreater',
    'isunordered',
    '_Exit',
    'acoshf',
    'acoshl',
    'acosh',
    'asinhf',
    'asinhl',
    'asinh',
    'atanhf',
    'atanhl',
    'atanh',
    'cabsf',
    'cabsl',
    'cabs',
    'cacosf',
    'cacoshf',
    'cacoshl',
    'cacosh',
    'cacosl',
    'cacos',
    'cargf',
    'cargl',
    'carg',
    'casinf',
    'casinhf',
    'casinhl',
    'casinh',
    'casinl',
    'casin',
    'catanf',
    'catanhf',
    'catanhl',
    'catanh',
    'catanl',
    'catan',
    'cbrtf',
    'cbrtl',
    'cbrt',
    'ccosf',
    'ccoshf',
    'ccoshl',
    'ccosh',
    'ccosl',
    'ccos',
    'cexpf',
    'cexpl',
    'cexp',
    'cimagf',
    'cimagl',
    'cimag',
    'clogf',
    'clogl',
    'clog',
    'conjf',
    'conjl',
    'conj',
    'copysignf',
    'copysignl',
    'copysign',
    'cpowf',
    'cpowl',
    'cpow',
    'cprojf',
    'cprojl',
    'cproj',
    'crealf',
    'creall',
    'creal',
    'csinf',
    'csinhf',
    'csinhl',
    'csinh',
    'csinl',
    'csin',
    'csqrtf',
    'csqrtl',
    'csqrt',
    'ctanf',
    'ctanhf',
    'ctanhl',
    'ctanh',
    'ctanl',
    'ctan',
    'erfcf',
    'erfcl',
    'erfc',
    'erff',
    'erfl',
    'erf',
    'exp2f',
    'exp2l',
    'exp2',
    'expm1f',
    'expm1l',
    'expm1',
    'fdimf',
    'fdiml',
    'fdim',
    'fmaf',
    'fmal',
    'fmaxf',
    'fmaxl',
    'fmax',
    'fma',
    'fminf',
    'fminl',
    'fmin',
    'hypotf',
    'hypotl',
    'hypot',
    'ilogbf',
    'ilogbl',
    'ilogb',
    'imaxabs',
    'isblank',
    'iswblank',
    'lgammaf',
    'lgammal',
    'lgamma',
    'llabs',
    'llrintf',
    'llrintl',
    'llrint',
    'llroundf',
    'llroundl',
    'llround',
    'log1pf',
    'log1pl',
    'log1p',
    'log2f',
    'log2l',
    'log2',
    'logbf',
    'logbl',
    'logb',
    'lrintf',
    'lrintl',
    'lrint',
    'lroundf',
    'lroundl',
    'lround',
    'nearbyintf',
    'nearbyintl',
    'nearbyint',
    'nextafterf',
    'nextafterl',
    'nextafter',
    'nexttowardf',
    'nexttowardl',
    'nexttoward',
    'remainderf',
    'remainderl',
    'remainder',
    'remquof',
    'remquol',
    'remquo',
    'rintf',
    'rintl',
    'rint',
    'roundf',
    'roundl',
    'round',
    'scalblnf',
    'scalblnl',
    'scalbln',
    'scalbnf',
    'scalbnl',
    'scalbn',
    'snprintf',
    'tgammaf',
    'tgammal',
    'tgamma',
    'truncf',
    'truncl',
    'trunc',
    'vfscanf',
    'vscanf',
    'vsnprintf',
    'acosf',
    'acosl',
    'asinf',
    'asinl',
    'atan2f',
    'atan2l',
    'atanf',
    'atanl',
    'ceilf',
    'ceill',
    'cosf',
    'coshf',
    'coshl',
    'cosl',
    'expf',
    'expl',
    'fabsf',
    'fabsl',
    'floorf',
    'floorl',
    'fmodf',
    'fmodl',
    'frexpf',
    'frexpl',
    'ldexpf',
    'ldexpl',
    'log10f',
    'log10l',
    'logf',
    'logl',
    'modfl',
    'modf',
    'powf',
    'powl',
    'sinf',
    'sinhf',
    'sinhl',
    'sinl',
    'sqrtf',
    'sqrtl',
    'tanf',
    'tanhf',
    'tanhl',
    'tanl',
    # Outside c99 and c89
    '_exit',
    'alloca',
    'bcmp',
    'bzero',
    'dcgettext',
    'dgettext',
    'dremf',
    'dreml',
    'drem',
    'exp10f',
    'exp10l',
    'exp10',
    'ffsll',
    'ffs',
    'fprintf_unlocked',
    'fputs_unlocked',
    'gammaf',
    'gammal',
    'gamma',
    'gammaf_r',
    'gammal_r',
    'gamma_r',
    'gettext',
    'index',
    'isascii',
    'j0f',
    'j0l',
    'j0',
    'j1f',
    'j1l',
    'j1',
    'jnf',
    'jnl',
    'jn',
    'lgammaf_r',
    'lgammal_r',
    'lgamma_r',
    'mempcpy',
    'pow10f',
    'pow10l',
    'pow10',
    'printf_unlocked',
    'rindex',
    'scalbf',
    'scalbl',
    'scalb',
    'signbit',
    'signbitf',
    'signbitl',
    'signbitd32',
    'signbitd64',
    'signbitd128',
    'significandf',
    'significandl',
    'significand',
    'sincosf',
    'sincosl',
    'sincos',
    'stpcpy',
    'stpncpy',
    'strcasecmp',
    'strdup',
    'strfmon',
    'strncasecmp',
    'strndup',
    'toascii',
    'y0f',
    'y0l',
    'y0',
    'y1f',
    'y1l',
    'y1',
    'ynf',
    'ynl',
    'yn',
    'abort',
    'abs',
    'acos',
    'asin',
    'atan2',
    'atan',
    'calloc',
    'ceil',
    'cosh',
    'cos',
    'exit',
    'exp',
    'fabs',
    'floor',
    'fmod',
    'fprintf',
    'fputs',
    'frexp',
    'fscanf',
    'labs',
    'ldexp',
    'log10',
    'log',
    'malloc',
    'memcmp',
    'memcpy',
    'memset',
    'modf',
    'modff',
    'modfl',
    'pow',
    'printf',
    'putchar',
    'puts',
    'scanf',
    'sinh',
    'sin',
    'snprintf',
    'sprintf',
    'sqrt',
    'sscanf',
    'strcat',
    'strchr',
    'strcmp',
    'strcpy',
    'strcspn',
    'strlen',
    'strncat',
    'strncmp',
    'strncpy',
    'strpbrk',
    'strrchr',
    'strspn',
    'strstr',
    'tanh',
    'tan',
    'vfprintf',
    'vprintf',
    'vsprintf'
]

IMPLICIT_FUNCTIONS = [
                         '__VERIFIER_assume',
                         # stdio.h
                         'fclose',
                         'clearerr',
                         'feof',
                         'ferror',
                         'fflush',
                         'fgetpos',
                         'fopen',
                         'fread',
                         'freopen',
                         'fseek',
                         'fsetpos',
                         'ftell',
                         'fwrite',
                         'remove',
                         'rename',
                         'rewind',
                         'setbuf',
                         'setvbuf',
                         'tmpfile',
                         'tmpnam',
                         'fprintf',
                         'printf',
                         'sprintf',
                         'vfprintf',
                         'vprintf',
                         'vsprintf',
                         'fscanf',
                         'scanf',
                         'sscanf',
                         'fgetc',
                         'fgets',
                         'fputc',
                         'fputs',
                         'getc',
                         'getchar',
                         'gets',
                         'putc',
                         'putchar',
                         'puts',
                         'ungetc',
                         'perror',
                         # stdlib.h
                         'atoi',
                         'atof',
                         'atol',
                         'atoll',
                         'strtod',
                         'strtol',
                         'strtoll',
                         'strtoq',
                         'strtold',
                         'strtof',
                         'strtoul',
                         'strtoull',
                         'calloc',
                         'free',
                         'malloc',
                         'realloc',
                         'alloca',
                         'valloc',
                         'abort',
                         'atexit',
                         'exit',
                         'getenv',
                         'system',
                         'bsearch',
                         'qsort',
                         'abs',
                         'div',
                         'labs',
                         'ldiv',
                         'mblen',
                         'mbstowcs',
                         'mbtowc',
                         'wcstombs',
                         'wctomb',
                         # string.h
                         'memchr',
                         'memcmp',
                         'memcpy',
                         'memmove',
                         'memset',
                         'strcat',
                         'strncat',
                         'strchr',
                         'strcmp',
                         'strncmp',
                         'strcoll',
                         'strcpy',
                         'strncpy',
                         'strcspn',
                         'strerror',
                         'strlen',
                         'strpbrk',
                         'strrchr',
                         'strspn',
                         'strstr',
                         'strtok',
                         'strxfrm',
                         # fenv.h
                         'feclearexcpt',
                         'feraiseexcept',
                         'fegetexceptflag',
                         'fesetexceptflag',
                         'fegetround',
                         'fesetround',
                         'fegetenv',
                         'fesetenv',
                         'feholdexcept',
                         'feupdateenv',
                         'fetestexcept',
                         '__underflow',
                         '__uflow',
                         '__overflow',
                         '_IO_getc',
                         '_IO_putc',
                         '_IO_feof',
                         '_IO_ferror',
                         '_IO_peekc_locked',
                         '_IO_flockfile',
                         '_IO_funlockfile',
                         '_IO_ftrylockfile',
                         '_IO_vfscanf',
                         '_IO_fprintf',
                         '_IO_padn',
                         '_IO_seekoff',
                         '_IO_seekpos',
                         '_IO_free_backup_area'
                     ] + GCC_BUILTINS + ['__' + g for g in GCC_BUILTINS
                                         ] + ["__builtin__" + g for g in GCC_BUILTINS]
