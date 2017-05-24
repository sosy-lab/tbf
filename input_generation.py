import utils
import os
import logging
import pycparser
from pycparser import c_generator
from abc import ABCMeta, abstractmethod


class BaseInputGenerator(object):
    __metaclass__ = ABCMeta

    var_counter = 0

    @abstractmethod
    def create_input_generation_cmds(self, filename):
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
        ast = self.parse_file(filename)
        r = self.get_ast_replacer()
        # ps is list of ast pieces that must still be appended (must be empty!), new_ast is the modified ast
        ps, new_ast = r.visit(ast)
        assert not ps  # Make sure that there are no ast pieces left that must be appended

        logging.debug("Prepared content")
        generator = c_generator.CGenerator()
        return generator.visit(new_ast)

    def parse_file(self, filename):
        preprocessed_filename = '.'.join(filename.split('/')[-1].split('.')[:-1] + ['i'])
        preprocessed_filename = utils.create_file_path(preprocessed_filename, temp_dir=True)
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
            p = utils.execute(preprocess_cmd)

        ast = pycparser.parse_file(preprocessed_filename)
        return ast

    def generate_input(self, filename, stop_flag=None):
        suffix = filename.split('.')[-1]
        file_to_analyze = '.'.join(os.path.basename(filename).split('.')[:-1] + [self.get_name(), suffix])
        file_to_analyze = utils.create_file_path(file_to_analyze, temp_dir=True)

        if os.path.exists(file_to_analyze):
            logging.warning("Prepared file already exists. Not preparing again.")
            return file_to_analyze

        prepared_content = self.prepare(filename)
        with open(file_to_analyze, 'w+') as new_file:
            new_file.write(prepared_content)

        cmds = self.create_input_generation_cmds(file_to_analyze)
        for cmd in cmds:
            result = utils.execute(cmd, env=self.get_run_env())
            if BaseInputGenerator.failed(result):
                raise utils.InputGenerationError('Generating input failed at command ' + ' '.join(cmd))
        return file_to_analyze
