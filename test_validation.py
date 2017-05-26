from abc import abstractmethod, ABCMeta
import witness_generation as wit_gen
import harness_generation as harness_gen
import logging
import utils
import os

valid_validators = ['cpachecker', 'uautomizer', 'cpa-w2t', 'fshell-w2t']


class ValidationConfig(object):

    def __init__(self, args):
        self.machine_model = args.machine_model

        if not self.machine_model:
            logging.warning("No machine model specified. Assuming 32 bit")
            self.machine_model = '32bit'

        self.use_execution = args.execution_validation
        self.use_witness_validation = args.witness_validation
        self.witness_validators = args.validators

        if self.witness_validators and not self.use_witness_validation:
            raise utils.ConfigError("Validators specified but no witness validation used (--witness-validation).")
        elif self.use_witness_validation and not self.witness_validators:
            raise utils.ConfigError("Witness validation used but not validators specified (--validators VAL).")
        elif self.witness_validators:
            for validator in self.witness_validators:
                if validator.lower() not in valid_validators:
                    raise utils.ConfigError("Validator not in list of known validators:"
                                            "{0} not in {1}".format(validator, valid_validators))


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

    def get_error_line(self, filename):
        with open(filename, 'r') as inp:
            content = inp.readlines()
        error_line = -1
        for line_num, line in enumerate(content, start=1):
            # Try to differentiate definition from call through the 'void' condition
            if utils.error_method in line and 'void' not in line:
                assert error_line == -1  # Assert that there's only one call to __VERIFIER_error()
                error_line = line_num
        assert error_line > 0  # Assert that there's a call to __VERIFIER_error
        return error_line

    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def create_all_witnesses(self, filename):
        pass

    def perform_witness_validation(self, filename, generator_thread):
        produced_witnesses = self.create_all_witnesses(filename)

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

    @abstractmethod
    def create_all_harnesses(self, filename):
        pass

    def perform_execution_validation(self, filename, generator_thread):
        produced_harnesses = self.create_all_harnesses(filename)

        validator = ExecutionRunner(self.config.machine_model)

        for harness in produced_harnesses:
            harness_name = harness['name']
            with open(harness_name, 'w+') as outp:
                outp.write(harness['content'])

            result = validator.run(filename, harness_name)

            logging.info('Results for %s: %s', harness_name, str(result))
            if [s for s in result if 'false' in s]:
                return False
        return True

    def check_inputs(self, filename, generator_thread=None):
        logging.debug('Checking inputs for file %s', filename)
        result = False
        if self.config.use_execution:
            result = self.perform_execution_validation(filename, generator_thread)
            logging.info("Execution validation says: " + str(result))

        if not result and self.config.use_witness_validation:
            result = self.perform_witness_validation(filename, generator_thread)
            logging.info("Witness validation says: " + str(result))


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
            compile_result = utils.execute(compile_cmd)

            if compile_result.returncode != 0:
                logging.warning("Compilation failed for harness {}".format(harness_file))

        return output_file

    def run(self, program_file, harness_file):
        executable = self.compile(program_file, harness_file)
        run_cmd = self._get_run_cmd(executable)
        run_result = utils.execute(run_cmd, quiet=True)

        if utils.error_return == run_result.returncode:
            return ['false']
        else:
            return ['true']


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

    def _get_cmd(self, program_file, witness_file):
        if not self.executable:
            self.executable = self.tool.executable()
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
               '--spec', utils.spec_file,
               '--validate', witness_file,
               '--file', program_file,
               machine_model]
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