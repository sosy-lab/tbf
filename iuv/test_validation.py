from abc import abstractmethod, ABCMeta
import witness_generation as wit_gen
import harness_generation as harness_gen
import logging
import utils
import os
from time import sleep
import re
from utils import TRUE, FALSE, UNKNOWN, ERROR

valid_validators = ['cpachecker', 'uautomizer', 'cpa-w2t', 'fshell-w2t']


class ValidationConfig(object):

    def __init__(self, args):
        self.machine_model = args.machine_model

        self.use_execution = args.execution_validation
        self.use_witness_validation = args.witness_validation
        self.witness_validators = args.validators if args.validators else []

        self.use_klee_replay = False
        if args.klee_replay_validation:
            if args.input_generator != "klee":
                raise utils.ConfigError("Klee-replay only works with klee as tester")
            else:
                logging.warning(
                    "Klee-replay only supports the machine architecture! Machine model specified not respected.")
                self.use_klee_replay = True

        if self.witness_validators and not self.use_witness_validation:
            raise utils.ConfigError("Validators specified but no witness validation used (--witness-validation).")
        elif self.use_witness_validation and not self.witness_validators:
            logging.warning("Witness validation used and no validator specified. Only generating witnesses.")
        elif self.witness_validators:
            for validator in self.witness_validators:
                if validator.lower() not in valid_validators:
                    raise utils.ConfigError("Validator not in list of known validators:"
                                            "{0} not in {1}".format(validator, valid_validators))
        elif not self.use_witness_validation and not self.use_execution and not self.use_klee_replay:
            raise utils.ConfigError("No validation technique specified. Specify --execution or --witness-validation .")

        self.convert_to_int = args.write_integers
        self.naive_verification = args.naive_verification


class TestValidator(object):

    __metaclass__ = ABCMeta

    def __init__(self, validation_config):
        self._nondet_var_map = None
        self.machine_model = validation_config.machine_model
        self.config = validation_config
        self.witness_creator = wit_gen.WitnessCreator()
        self.harness_creator = harness_gen.HarnessCreator()

        self.naive_verification = validation_config.naive_verification

        # If a void appears in a line, there must be something between
        # the void and the __VERIFIER_error() symbol - otherwise
        # it is a function definition/declaration.
        self.error_method_pattern = re.compile('((?!void).)*(void.*\S.*)?__VERIFIER_error\(\) *;.*')

        self.statistics = utils.statistics.new('Test Validator ' + self.get_name())
        self.timer_validation = utils.Stopwatch()
        self.statistics.add_value('Time for validation', self.timer_validation)
        self.timer_witness_validation = utils.Stopwatch()
        self.statistics.add_value('Time for witness validation', self.timer_witness_validation)
        self.counter_size_witnesses = utils.Counter()
        self.statistics.add_value('Total size of witnesses', self.counter_size_witnesses)
        self.timer_execution_validation = utils.Stopwatch()
        self.statistics.add_value('Time for execution validation', self.timer_execution_validation)
        self.counter_size_harnesses = utils.Counter()
        self.statistics.add_value('Total size of harnesses', self.counter_size_harnesses)

        self.counter_handled_test_cases = utils.Counter()
        self.statistics.add_value('Number of looked-at test cases', self.counter_handled_test_cases)

        self.final_test_vector_size = utils.Constant()
        self.statistics.add_value("Size of successful test vector", self.final_test_vector_size)

    def get_error_lines(self, filename):
        with open(filename, 'r') as inp:
            content = inp.readlines()

        err_lines = list()
        for line_num, line in enumerate(content, start=1):
            # Try to differentiate definition from call through the 'void' condition
            if self.error_method_pattern.match(line):
                err_lines.append(line_num)
        assert err_lines  # Asser that there is at least one error call
        return err_lines

    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def create_all_witnesses(self, filename, visited_tests, nondet_methods):
        pass

    @abstractmethod
    def create_witness(self, filename, test_file, test_vector, nondet_methods):
        pass

    @abstractmethod
    def get_test_files(self, visited_tests):
        pass

    def decide_final_verdict(self, final_result):
        if final_result.is_positive() or not self.naive_verification:
            return final_result
        else:
            return utils.VerdictTrue()

    def perform_witness_validation(self, filename, generator_thread):
        validator = ValidationRunner(self.config.witness_validators)
        nondet_methods = utils.get_nondet_methods()
        visited_tests = set()
        while generator_thread and not generator_thread.ready():
            try:
                result = self._m(filename, validator, visited_tests, nondet_methods)
                if result.is_positive():
                    return result
                sleep(0.001)  # Sleep for 1 millisecond
            except utils.InputGenerationError:  # Just capture here and retry as long as the thread is alive
                pass
        result = self._m(filename, validator, visited_tests)
        return self.decide_final_verdict(result)

    def _m(self, filename, validator, visited_tests, nondet_methods):
        produced_witnesses = self.create_all_witnesses(filename, visited_tests, nondet_methods)
        for witness in produced_witnesses:
            logging.debug('Looking at witness %s', witness['name'])
            witness_name = witness['name']
            content_to_write = witness['content']
            self.counter_size_witnesses.inc(len(content_to_write))
            with open(witness_name, 'w+') as outp:
                outp.write(witness['content'])
            self.timer_witness_validation.start()
            self.timer_validation.start()
            try:
                verdicts = validator.run(filename, witness_name)
            finally:
                self.timer_witness_validation.stop()
                self.timer_validation.stop()
            self.counter_handled_test_cases.inc()
            logging.info('Results for %s: %s', witness_name, str(verdicts))
            if any(['false' in v.lower() for v in verdicts]):
                self.final_test_vector_size.value = len(witness['vector'])
                return utils.VerdictFalse(witness['origin'], witness['vector'], None, witness_name)

        return utils.VerdictUnknown()

    def create_all_test_vectors(self, filename, visited_tests):
        all_vectors = list()
        new_test_files = self.get_test_files(visited_tests)
        if len(new_test_files) > 0:
            logging.info("Looking at %s test files", len(new_test_files))
        for test_file in new_test_files:
            logging.debug('Looking at test case %s', test_file)
            test_name = utils.get_file_name(test_file)
            assert test_name not in visited_tests
            assert os.path.exists(test_file)
            visited_tests.add(test_name)
            test_vector = self.get_test_vector(test_file)
            all_vectors.append(test_vector)
        return all_vectors

    @abstractmethod
    def create_all_harnesses(self, filename, visited_tests, nondet_methods):
        pass

    @abstractmethod
    def create_harness(self, filename, test_file, test_vector, nondet_methods):
        pass

    @abstractmethod
    def get_test_vector(self, test_file):
        pass

    def perform_execution_validation(self, filename, generator_thread):
        validator = ExecutionRunnerTwo(self.config.machine_model, self.get_name())
        visited_tests = set()
        while generator_thread and not generator_thread.ready():
            try:
                result = self._hs(filename, validator, visited_tests)
                if result.is_positive():
                    return result
                sleep(0.001)  # Sleep for 1 millisecond
            except utils.InputGenerationError:  # Just capture here and retry as long as the thread is alive
                pass

        result = self._hs(filename, validator, visited_tests)
        return self.decide_final_verdict(result)

    def _hs(self, filename, validator, visited_tests):
        test_vectors = self.create_all_test_vectors(filename, visited_tests)

        for vector in test_vectors:
            self.timer_execution_validation.start()
            self.timer_validation.start()
            try:
                verdicts = validator.run(filename, vector)
            finally:
                self.timer_execution_validation.stop()
                self.timer_validation.stop()
            self.counter_handled_test_cases.inc()

            logging.debug('Results for %s: %s', vector, str(verdicts))
            if any([v == FALSE for v in verdicts]):
                self.final_test_vector_size.value = len(vector)
                return utils.VerdictFalse(vector.origin, vector)
        return utils.VerdictUnknown()

    def _k(self, filename, validator, visited_tests):
        test_files = self.get_test_files(visited_tests)

        for test in test_files:
            self.timer_execution_validation.start()
            self.timer_validation.start()
            try:
                verdicts = validator.run(filename, test)
            finally:
                self.timer_execution_validation.stop()
                self.timer_validation.stop()
            self.counter_handled_test_cases.inc()

            logging.debug('Results for %s: %s', test, str(verdicts))
            if any([v == FALSE for v in verdicts]):
                return utils.VerdictFalse(test)
        return utils.VerdictUnknown()

    def perform_klee_replay_validation(self, filename, generator_thread):
        validator = KleeReplayRunner(self.config.machine_model)

        visited_tests = set()
        while generator_thread and not generator_thread.ready():
            try:
                result = self._k(filename, validator, visited_tests)
                if result.is_positive():
                    return result
                sleep(0.001)  # Sleep for 1 millisecond
            except utils.InputGenerationError:  # Just capture here and retry as long as the thread is alive
                pass

        result = self._k(filename, validator, visited_tests)
        return self.decide_final_verdict(result)

    def check_inputs(self, filename, generator_thread=None):
        logging.debug('Checking inputs for file %s', filename)
        result = utils.VerdictUnknown()

        if self.config.use_klee_replay:
            result = self.perform_klee_replay_validation(filename, generator_thread)
            logging.info("Klee-replay validation says: " + str(result))

        if not result.is_positive() and self.config.use_execution:
            result = self.perform_execution_validation(filename, generator_thread)
            logging.info("Execution validation says: " + str(result))

        if not result.is_positive() and self.config.use_witness_validation:
            result = self.perform_witness_validation(filename, generator_thread)
            logging.info("Witness validation says: " + str(result))

        if result.is_positive():
            test_vector = result.test_vector
            if not test_vector:
                test_vector = self.get_test_vector(result.test)
            if result.witness is None:
                nondet_methods = utils.get_nondet_methods()
                witness = self.create_witness(filename, result.test, test_vector, nondet_methods)
                with open(witness['name'], 'w+') as outp:
                    outp.write(witness['content'])
                result.witness = witness['name']
            if result.harness is None:
                nondet_methods = utils.get_nondet_methods()
                harness = self.create_harness(filename, result.test, test_vector, nondet_methods)
                with open(harness['name'], 'w+') as outp:
                    outp.write(harness['content'])
                result.harness = harness['name']

        return result


class ExecutionRunner(object):

    def __init__(self, machine_model):
        self.machine_model = machine_model

    def _get_compile_cmd(self, program_file, harness_file, output_file, c_version='c11'):
        if '32' in self.machine_model:
            mm_arg = '-m32'
        elif '64' in self.machine_model:
            mm_arg = '-m64'
        else:
            raise AssertionError("Unhandled machine model: ", self.machine_model)

        cmd = ['gcc']
        cmd += ['-std={}'.format(c_version),
                mm_arg,
                '-D__alias__(x)=',
                '-o', output_file,
                '-include', program_file,
                harness_file]

        return cmd

    def _get_run_cmd(self, executable):
        return [executable]

    def compile(self, program_file, harness_file):
        output_file = utils.get_file_path('a.out', temp_dir=True)
        compile_cmd = self._get_compile_cmd(program_file, harness_file, output_file)
        compile_result = utils.execute(compile_cmd, quiet=True)

        if compile_result.returncode != 0:
            compile_cmd = self._get_compile_cmd(program_file, harness_file, output_file, 'c90')
            compile_result = utils.execute(compile_cmd, quiet=True)

            if compile_result.returncode != 0:
                raise utils.CompileError("Compilation failed for harness {}".format(harness_file))
                return None

        return output_file

    def run(self, program_file, harness_file):
        executable = self.compile(program_file, harness_file)
        if executable:
            run_cmd = self._get_run_cmd(executable)
            run_result = utils.execute(run_cmd, quiet=True, err_to_output=False)

            if utils.found_err(run_result):
                return [FALSE]
            else:
                return [UNKNOWN]
        else:
            return [ERROR]


class ExecutionRunnerTwo(ExecutionRunner):

    def __init__(self, machine_model, producer_name):
        super().__init__(machine_model)
        self.harness = None
        self.producer = producer_name
        self.harness_generator = harness_gen.HarnessCreator()

    def get_executable_harness(self, program_file):
        if not self.harness:
            self.harness = self._create_executable_harness(program_file)
        return self.harness

    def _create_executable_harness(self, program_file):
        nondet_methods = utils.get_nondet_methods()
        harness_content = self.harness_generator.create_harness(nondet_methods, utils.error_method)
        harness_file = 'harness.c'
        with open(harness_file, 'w+') as outp:
            outp.write(harness_content)
        return self.compile(program_file, harness_file)

    def run(self, program_file, test_vector):
        executable = self.get_executable_harness(program_file)
        input_vector = utils.get_input_vector(test_vector)

        if executable:
            run_cmd = self._get_run_cmd(executable)
            run_result = utils.execute(run_cmd, quiet=True, err_to_output=False, input_str=input_vector, timelimit=5)

            if utils.found_err(run_result):
                return [FALSE]
            else:
                return [UNKNOWN]
        else:
            return [ERROR]


class KleeReplayRunner(object):

    def __init__(self, machine_model):
        self.machine_model = machine_model
        self.executable_name = './a.out'
        self.executable = None
        if os.path.exists(self.executable_name):
            os.remove(self.executable_name)

    def run(self, program_file, test_file):
        import klee

        klee_prepared_file = utils.get_prepared_name(program_file, klee.name)
        if not self.executable:
            compile_cmd = ["gcc", "-L", klee.lib_dir, "-o", self.executable_name, klee_prepared_file, "-lkleeRuntest"]
            utils.execute(compile_cmd)
            self.executable = self.executable_name

        if not os.path.exists(self.executable_name):
            return [ERROR]

        curr_env = utils.get_env()
        curr_env['KTEST_FILE'] = test_file

        result = utils.execute([self.executable], env=curr_env, err_to_output=False)

        if utils.found_err(result):
            return [FALSE]
        else:
            return [UNKNOWN]


class ValidationRunner(object):

    def __init__(self, validators):
        self.validators = list()
        validators_used = set()
        for val in [v.lower() for v in validators]:
            if val == 'cpachecker' and 'cpachecker' not in validators_used:
                self.validators.append(CPAcheckerValidator())
                validators_used.add('cpachecker')
            elif val == 'uautomizer' and 'uautomizer' not in validators_used:
                self.validators.append(UAutomizerValidator())
                validators_used.add('uautomizer')
            elif val == 'cpa-w2t' and 'cpa-w2t' not in validators_used:
                self.validators.append(CpaW2t())
                validators_used.add('cpa-w2t')
            elif val == 'fshell-w2t' and 'fshell-w2t' not in validators_used:
                self.validators.append(FShellW2t())
                validators_used.add('fshell-w2t')
            else:
                raise utils.ConfigError('Invalid validator list: ' + validators)

    def run(self, program_file, witness_file):
        results = []
        for validator in self.validators:
            logging.debug("Running %s on %s", validator, witness_file)
            result = validator.validate(program_file, witness_file)
            results.append(result)

        return results


class Validator(object):

    __metaclass__ = ABCMeta

    def __init__(self, tool_name):
        self.tool = utils.import_tool(tool_name)

    def validate(self, program_file, witness_file):
        # err_to_output=True is important so that messages to stderr are in correct relation to messages to stdout!
        # This may be important for determining the run result.
        cmd_result = utils.execute(self._get_cmd(program_file, witness_file), quiet=True, err_to_output=True)

        returncode = cmd_result.returncode
        # Execute returns a negative returncode -N if the process was killed by signal N
        if returncode < 0:
            returnsignal = - returncode
        else:
            returnsignal = 0

        if cmd_result.stderr:
            tool_output = cmd_result.stderr.split('\n')
        else:
            tool_output = list()
        tool_output += cmd_result.stdout.split('\n')
        # Remove last line if empty. FShell expects no empty line at the end.
        if len(tool_output) >= 1 and not tool_output[-1]:
            tool_output = tool_output[:-1]
        validation_result = self.tool.determine_result(returncode, returnsignal, tool_output, isTimeout=False)
        return validation_result

    @abstractmethod
    def _get_cmd(self, program_file, witness_file):
        pass


class CPAcheckerValidator(Validator):

    def __init__(self):
        super().__init__('cpachecker')
        self.executable = None  # executable will compile CPAchecker when called, so only do this if we really validate
        self.cpa_directory = None

    def _get_cmd(self, program_file, witness_file):
        if not self.executable:
            import shutil
            self.executable = self.tool.executable()
            self.cpa_directory = os.path.join(os.path.dirname(self.executable), '..')
            config_copy_dir = utils.get_file_path('config', temp_dir=True)
            if not os.path.exists(config_copy_dir):
                copy_dir = os.path.join(self.cpa_directory, 'config')
                shutil.copytree(copy_dir, config_copy_dir)
        return [self.executable] + \
               utils.get_cpachecker_options(witness_file) +\
               ['-witnessValidation', program_file]


class UAutomizerValidator(Validator):

    def __init__(self):
        super().__init__('ultimateautomizer')
        self.executable = self.tool.executable()

    def _get_cmd(self, program_file, witness_file):
        machine_model = utils.get_machine_model(witness_file)
        if '32' in machine_model:
            machine_model = '32bit'
        elif '64' in machine_model:
            machine_model = '64bit'
        else:
            raise AssertionError("Unhandled machine model: " + machine_model)

        cmd = [self.executable,
               '--validate', witness_file,
               utils.spec_file,
               machine_model,
               program_file]
        return cmd


class CpaW2t(Validator):

    def __init__(self):
        super().__init__('cpa-witness2test')
        self.executable = None  # executable will compile CPAchecker when called, so only do this if we really validate

    def _get_cmd(self, program_file, witness_file):
        if not self.executable:
            self.executable = self.tool.executable()
        return [self.executable] + \
               utils.get_cpachecker_options(witness_file) +\
               ['-witness2test', program_file]


class FShellW2t(Validator):

    def __init__(self):
        super().__init__('witness2test')
        self.executable = self.tool.executable()
        self.repo = os.path.dirname(os.path.abspath(self.executable))

    def _get_cmd(self, program_file, witness_file):
        machine_model = utils.get_machine_model(witness_file)
        if '32' in machine_model:
            machine_model = '-m32'
        elif '64' in machine_model:
            machine_model = '-m64'
        else:
            raise AssertionError('Unhandled machine model: ' + machine_model)

        return [self.executable,
                '--propertyfile', utils.spec_file,
                '--graphml-witness', witness_file,
                machine_model,
                program_file]

    def validate(self, program_file, witness_file):
        """Overwrites Validator.validate(...)."""
        # FShell-w2t only works if it is run from its repository. Because of this,
        # we always have to change directories, first.
        old_dir = os.path.abspath('.')
        os.chdir(self.repo)
        result = super().validate(program_file, witness_file)
        os.chdir(old_dir)  # And we change directories back to the original one
        return result