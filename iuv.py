#!/usr/bin/python3

import sys
import os
import logging
import argparse

import klee
import utils

import threading
from abc import ABCMeta, abstractmethod

import pycparser
from pycparser import c_generator


logging.basicConfig(level=logging.INFO)

__VERSION__ = 0.1

ast = None


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


class BaseInputGenerator(object):
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
        name_new_file = utils.create_file_path(name_new_file, temp_dir=True)
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
            result = utils.execute(cmd, env=self.get_run_env())
            if BaseInputGenerator.failed(result):
                raise utils.InputGenerationError('Generating input failed at command ' + ' '.join(cmd))

    def check_inputs(self, filename, generator_thread=None):
        prepared_file = self.prepare(filename)
        produced_witnesses = self.create_all_witnesses(prepared_file)

        validator = ValidationRunner()

        for witness in produced_witnesses:
            witness_name = witness['name']
            with open(witness_name, 'w+') as outp:
                outp.write(witness['content'])

            results = validator.run(prepared_file, witness_name)

            logging.info('Results for %s: %s', witness_name, str(results))
            if [s for s in results if 'false' in s]:
                return True
        return False


def _create_cli_arg_parser():
    parser = argparse.ArgumentParser(description='Toolchain for test-input using verifier', add_help=False)

    args = parser.add_mutually_exclusive_group()
    run_args = args.add_argument_group()
    input_generator_args = run_args.add_argument_group(title="Input generation args",
                                                       description="arguments for input generation"
                                                       )
    input_generator_args.add_argument("--input-generator", '-i',
                                      dest="input_generator",
                                      action="store",  # TODO: Change to only allow enum selection
                                      required=True,
                                      choices=['klee', 'crest'],
                                      help="input generator to use"
                                      )
    input_generator_args.add_argument("--ig-timelimit",
                                      dest="ig_timelimit",
                                      help="time limit (in s) for input generation.\n"
                                           + "After this limit, input generation"
                                           + " stops and analysis is performed\nwith the inputs generated up"
                                           + " to this point."
                                      )

    run_args.add_argument('--verbose', '-v',
                          dest="log_verbose",
                          action='store_true',
                          default=False,
                          help="print verbose information"
                          )

    run_args.add_argument('--no-parallel',
                          dest='run_parallel',
                          action='store_false',
                          default=True,
                          help="do not run input generation and tests in parallel"
                          )

    run_args.add_argument("file",
                          type=str,
                          help="file to verify"
                          )

    args.add_argument("--version",
                      action="version", version='{}'.format(__VERSION__)
                      )
    args.add_argument('--help', '-h',
                      action='help'
                      )
    return parser


def _parse_cli_args(argv):
    parser = _create_cli_arg_parser()
    return parser.parse_args(argv)


def _get_input_generator_module(args):
    input_generator = args.input_generator.lower()
    if input_generator == 'klee':
        return klee.InputGenerator(args.ig_timelimit, args.log_verbose)
    elif input_generator == 'crest':
        return crest.InputGenerator(args.ig_timelimit, args.log_verbose)
    else:
        raise AssertionError('Unhandled input generator: ' + input_generator)


def run():
    args = _parse_cli_args(sys.argv[1:])

    filename = os.path.abspath(args.file)
    module = _get_input_generator_module(args)

    if args.run_parallel:
        stop_event = threading.Event()
        generator_thread = threading.Thread(target=module.generate_input, args=(filename, stop_event))
        generator_thread.start()
    else:
        stop_event = None
        generator_thread = None
        module.generate_input(filename)

    error_reached = module.check_inputs(filename, generator_thread)

    if stop_event:
        stop_event.set()

    if error_reached:
        print("IUV: FALSE")
    else:
        print("IUV: UNKNOWN")

if __name__ == '__main__':
    default_err = "Unknown error"
    try:
        run()

    except utils.CompileError as e:
        logging.error("Compile error: %s", e.msg if e.msg else default_err)
    except utils.InputGenerationError as e:
        logging.error("Input generation error: %s", e.msg if e.msg else default_err)
    except utils.ParseError as e:
        logging.error("Parse error: %s", e.msg if e.msg else default_err)
