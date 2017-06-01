import utils
import os
import logging
import re
from abc import ABCMeta, abstractmethod


class BaseInputGenerator(object):
    __metaclass__ = ABCMeta

    var_counter = 0

    @abstractmethod
    def create_input_generation_cmds(self, filename):
        pass

    @abstractmethod
    def get_name(self):
        return None

    @abstractmethod
    def get_run_env(self):
        return os.environ

    @staticmethod
    def failed(result):
        return result.returncode < 0

    def __init__(self, timelimit, machine_model):
        self.machine_model = machine_model
        self.timelimit = int(timelimit) if timelimit else 0

    @abstractmethod
    def prepare(self, filecontent):
        pass

    def prepare0(self, filecontent):
        content = filecontent
        content += '\n'
        content += self._get_error_dummy()
        return self.prepare(content)

    def _get_error_dummy(self):
        return 'void ' + utils.error_method + '() { exit(107); }\n'

    def generate_input(self, filename, stop_flag=None):
        suffix = 'c'
        file_to_analyze = '.'.join(os.path.basename(filename).split('.')[:-1] + [self.get_name(), suffix])
        file_to_analyze = utils.get_file_path(file_to_analyze, temp_dir=True)

        with open(filename, 'r') as outp:
            filecontent = outp.read()

        if os.path.exists(file_to_analyze):
            logging.warning("Prepared file already exists. Not preparing again.")
            return file_to_analyze

        prepared_content = self.prepare0(filecontent)
        with open(file_to_analyze, 'w+') as new_file:
            new_file.write(prepared_content)

        cmds = self.create_input_generation_cmds(file_to_analyze)
        for cmd in cmds:
            result = utils.execute(cmd, env=self.get_run_env(), quiet=True, err_to_output=True)
            if BaseInputGenerator.failed(result):
                raise utils.InputGenerationError('Generating input failed at command ' + ' '.join(cmd))
        return file_to_analyze
