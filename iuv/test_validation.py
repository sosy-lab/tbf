from abc import abstractmethod, ABCMeta
import witness_generation as wit_gen
import harness_generation as harness_gen
import logging
import utils
import os
from time import sleep
import re
from utils import FALSE, UNKNOWN, ERROR

valid_validators = ['cpachecker', 'uautomizer', 'cpa-w2t', 'fshell-w2t']


class ValidationConfig(object):

    def __init__(self, args):
        self.machine_model = args.machine_model

        if not self.machine_model:
            logging.warning("No machine model specified. Assuming 32 bit")
            self.machine_model = '32bit'

        self.use_execution = args.execution_validation
        self.use_witness_validation = args.witness_validation
        self.witness_validators = args.validators if args.validators else []

        if self.witness_validators and not self.use_witness_validation:
            raise utils.ConfigError("Validators specified but no witness validation used (--witness-validation).")
        elif self.use_witness_validation and not self.witness_validators:
            logging.warning("Witness validation used and no validator specified. Only generating witnesses.")
        elif self.witness_validators:
            for validator in self.witness_validators:
                if validator.lower() not in valid_validators:
                    raise utils.ConfigError("Validator not in list of known validators:"
                                            "{0} not in {1}".format(validator, valid_validators))
        elif not self.use_witness_validation and not self.use_execution:
            raise utils.ConfigError("No validation technique specified. Specify --execution or --witness-validation .")

        self.convert_to_int = args.write_integers


class TestValidator(object):

    __metaclass__ = ABCMeta

    def __init__(self, validation_config):
        self._nondet_var_map = None
        self.machine_model = validation_config.machine_model
        self.config = validation_config
        if self.config.use_witness_validation:
            self.witness_creator = wit_gen.WitnessCreator()
        if self.config.use_execution:
            self.harness_creator = harness_gen.HarnessCreator()

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

    def get_error_line(self, filename):
        with open(filename, 'r') as inp:
            content = inp.readlines()
        error_line = -1

        for line_num, line in enumerate(content, start=1):
            # Try to differentiate definition from call through the 'void' condition
            if self.error_method_pattern.match(line):
                assert error_line == -1  # Assert that there's only one call to __VERIFIER_error()
                error_line = line_num
        assert error_line > 0  # Assert that there's a call to __VERIFIER_error
        return error_line

    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def create_all_witnesses(self, filename, visited_tests):
        pass

    def perform_witness_validation(self, filename, generator_thread):
        self.timer_witness_validation.start()
        try:
            validator = ValidationRunner(self.config.witness_validators)

            visited_tests = set()
            while generator_thread and generator_thread.is_alive():
                try:
                    result = self._m(filename, validator, visited_tests)
                    if result == FALSE:
                        return FALSE
                    sleep(0.001)  # Sleep for 1 millisecond
                except utils.InputGenerationError as e:  # Just capture here and retry as long as the thread is alive
                    pass
            return self._m(filename, validator, visited_tests)
        finally:
            self.timer_witness_validation.stop()

    def _m(self, filename, validator, visited_tests):
        produced_witnesses = self.create_all_witnesses(filename, visited_tests)

        for witness in produced_witnesses:
            logging.debug('Looking at witness %s', witness['name'])
            witness_name = witness['name']
            content_to_write = witness['content']
            self.counter_size_witnesses.inc(len(content_to_write))
            with open(witness_name, 'w+') as outp:
                outp.write(witness['content'])

            results = validator.run(filename, witness_name)
            self.counter_handled_test_cases.inc()

            logging.info('Results for %s: %s', witness_name, str(results))
            if [s for s in results if FALSE in s]:
                self.final_test_vector_size.value = len(witness['vector'])
                return FALSE
        return UNKNOWN

    @abstractmethod
    def create_all_harnesses(self, filename, visited_tests):
        pass

    def perform_execution_validation(self, filename, generator_thread):
        self.timer_execution_validation.start()
        try:
            validator = ExecutionRunner(self.config.machine_model)

            visited_tests = set()
            while generator_thread and generator_thread.is_alive():
                try:
                    result = self._h(filename, validator, visited_tests)
                    if result == FALSE:
                        return result
                    sleep(0.001)  # Sleep for 1 millisecond
                except utils.InputGenerationError as e:  # Just capture here and retry as long as the thread is alive
                    pass

            return self._h(filename, validator, visited_tests)
        finally:
            self.timer_execution_validation.stop()

    def _h(self, filename, validator, visited_tests):
        produced_harnesses = self.create_all_harnesses(filename, visited_tests)

        for harness in produced_harnesses:
            harness_name = harness['name']
            content_to_write = harness['content']
            self.counter_size_harnesses.inc(len(content_to_write))
            with open(harness_name, 'w+') as outp:
                outp.write(content_to_write)

            result = validator.run(filename, harness_name)
            self.counter_handled_test_cases.inc()

            logging.debug('Results for %s: %s', harness_name, str(result))
            if [s for s in result if FALSE in s]:
                self.final_test_vector_size.value = len(harness['vector'])
                return FALSE
        return UNKNOWN

    def check_inputs(self, filename, generator_thread=None):
        self.timer_validation.start()
        try:
            logging.debug('Checking inputs for file %s', filename)
            result = 'unknown'
            if self.config.use_execution:
                result = self.perform_execution_validation(filename, generator_thread)
                logging.info("Execution validation says: " + str(result))

            if result != 'false' and self.config.use_witness_validation:
                result = self.perform_witness_validation(filename, generator_thread)
                logging.info("Witness validation says: " + str(result))
            return result
        finally:
            self.timer_validation.stop()


class ExecutionRunner(object):

    def __init__(self, machine_model):
        self.machine_model = machine_model

    def _get_compile_cmd(self, program_file, harness_file, output_file, c_version='c11'):
        cmd = ['gcc']
        if '32' in self.machine_model:
            cmd.append('-m32')
        elif '64' in self.machine_model:
            cmd.append('-m64')
        else:
            raise AssertionError('Unhandled machine model: ' + self.machine_model)

        cmd += ['-std={}'.format(c_version),
                '-D__alias__(x)=',
                '-o', output_file,
                harness_file,
                program_file]

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
            run_result = utils.execute(run_cmd, quiet=True)

            if utils.error_return == run_result.returncode:
                return [FALSE]
            else:
                return [UNKNOWN]
        else:
            return [ERROR]


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
            copy_dir = os.path.join(self.cpa_directory, 'config')
            config_copy_dir = utils.get_file_path('config', temp_dir=True)
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