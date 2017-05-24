from abc import abstractmethod, ABCMeta
import logging
import utils
import os


class TestValidator(object):

    __metaclass__ = ABCMeta

    def __init__(self, machine_model='32bit'):
        self._nondet_var_map = None
        self.machine_model = machine_model

    def get_nondet_var_map(self, filename):
        """
        Returns data structure with information about all non-deterministic variables.
        Expected structure: var_map[variable_name] = {'line': line_number, 'origin file': source file,}
        """
        if not self._nondet_var_map:
            self._nondet_var_map = self.create_nondet_var_map(filename)
        return self._nondet_var_map

    @abstractmethod
    def create_nondet_var_map(self, filename):
        pass

    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def create_all_witnesses(self, filename):
        pass

    def check_inputs(self, filename, generator_thread=None):
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


class ValidationRunner(object):

    def __init__(self):
        self.validators = [CpaW2t(), FShellW2t()]

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
        self.executable = self.tool.executable()

    def validate(self, program_file, witness_file):
        cmd_result = utils.execute(self._get_cmd(program_file, witness_file), quiet=True, log_output=False)

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


class CPAcheckerValidator(object):

    def __init__(self):
        self.tool = utils.import_tool('cpachecker')
        self.executable = self.tool.executable()

    def _get_cmd(self, program_file, witness_file):
        return [self.executable] + \
               utils.get_cpachecker_options(witness_file) +\
               ['-witnessValidation', program_file]


class UAutomizerValidator(Validator):

    def __init__(self):
        super().__init__('ultimateautomizer')

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

    def _get_cmd(self, program_file, witness_file):
        return [self.executable] + \
               utils.get_cpachecker_options(witness_file) +\
               ['-witness2test', program_file]


class FShellW2t(Validator):

    def __init__(self):
        super().__init__('witness2test')
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