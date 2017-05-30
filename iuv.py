#!/usr/bin/python3

import sys
import os
import logging
import argparse

import klee
import crest
import utils
from utils import FALSE

import threading
from test_validation import ValidationConfig

logging.basicConfig(level=logging.INFO)

__VERSION__ = 0.1

ast = None


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
    validation_args = run_args.add_argument_group('Validation')
    witness_validation_args = validation_args.add_argument_group('Witness validation')
    witness_validation_args.add_argument('--witness-validation',
                                         dest="witness_validation",
                                         action='store_true',
                                         default=False,
                                         help="use witness validation to find successful test vector"
                                         )

    witness_validation_args.add_argument('--validators',
                                         dest="validators",
                                         nargs="+",
                                         help="witness validators to use for witness validation."
                                              " Requires parameter --witness-validation to be specified to be effective.")

    validation_args.add_argument('--execution',
                                 dest="execution_validation",
                                 action="store_true",
                                 default=False,
                                 help="use test execution to find successful test vector"
                                 )

    machine_model_args = run_args.add_mutually_exclusive_group()
    machine_model_args.add_argument('-32',
                                    dest="machine_model",
                                    action="store_const",
                                    const="32bit",
                                    help="Use 32 bit machine model"
                                    )
    machine_model_args.add_argument('-64',
                                    dest="machine_model",
                                    action="store_const",
                                    const="64bit",
                                    help="Use 64 bit machine model")

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


def _get_validator_module(args):
    validator = args.input_generator.lower()
    validation_config = ValidationConfig(args)
    if validator == 'klee':
        return klee.KleeTestValidator(validation_config)
    elif validator == 'crest':
        return crest.CrestTestValidator(validation_config)
    else:
        raise AssertionError('Unhandled validator: ' + validator)


def run():
    args = _parse_cli_args(sys.argv[1:])

    filename = os.path.abspath(args.file)
    inp_module = _get_input_generator_module(args)

    old_dir = os.path.abspath('.')
    os.chdir(utils.tmp)
    if args.run_parallel:
        stop_event = threading.Event()
        generator_thread = threading.Thread(target=inp_module.generate_input, args=(filename, stop_event))
        generator_thread.start()
    else:
        stop_event = None
        generator_thread = None
        file_for_analysis = inp_module.generate_input(filename)

    validator_module = _get_validator_module(args)
    validation_result = validator_module.check_inputs(filename, generator_thread)

    if stop_event:
        stop_event.set()

    os.chdir(old_dir)
    if validation_result == FALSE:
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
