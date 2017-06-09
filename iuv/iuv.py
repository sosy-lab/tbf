#!/usr/bin/python3

import sys
import os
import logging
import argparse

import cpatiger
import klee
import crest
import utils
import shutil

import threading

from test_validation import ValidationConfig

logging.basicConfig(level=logging.DEBUG)

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
                                      action="store",
                                      required=True,
                                      choices=['klee', 'crest', 'cpatiger'],
                                      help="input generator to use"
                                      )
    input_generator_args.add_argument("--ig-timelimit",
                                      dest="ig_timelimit",
                                      help="time limit (in s) for input generation.\n"
                                           + "After this limit, input generation"
                                           + " stops and analysis is performed\nwith the inputs generated up"
                                           + " to this point."
                                      )
    input_generator_args.add_argument("--no-write-integers",
                                      dest="write_integers",
                                      action='store_false',
                                      default=True,
                                      help="always write test vector values as integer values."
                                           "E.g., klee uses multi-character chars by default."
                                           "Given this argument, these values are converted to integers."
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
        return klee.InputGenerator(args.ig_timelimit, args.log_verbose, machine_model=args.machine_model)
    elif input_generator == 'crest':
        return crest.InputGenerator(args.ig_timelimit, args.log_verbose, machine_model=args.machine_model)
    elif input_generator == 'cpatiger':
        return cpatiger.InputGenerator(args.ig_timelimit, args.log_verbose, machine_model=args.machine_model)
    else:
        raise AssertionError('Unhandled input generator: ' + input_generator)


def _get_validator_module(args):
    validator = args.input_generator.lower()
    validation_config = ValidationConfig(args)
    if validator == 'klee':
        return klee.KleeTestValidator(validation_config)
    elif validator == 'crest':
        return crest.CrestTestValidator(validation_config)
    elif validator == 'cpatiger':
        return cpatiger.CpaTigerTestValidator(validation_config)
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
        inp_module.generate_input(filename)

    validator_module = _get_validator_module(args)
    validation_result = validator_module.check_inputs(filename, generator_thread)

    if validation_result.is_positive():
        test_name = os.path.basename(validation_result.test)
        persistent_test = utils.get_file_path(test_name, temp_dir=False)
        shutil.copy(validation_result.test, persistent_test)
        for proof in validation_result.harness, validation_result.witness:
            proof_name = os.path.basename(proof)
            if proof_name.endswith('.harness.c'):
                persistent_proof = utils.get_file_path('harness.c', temp_dir=False)
            else:
                assert proof_name.endswith('.witness.graphml')
                persistent_proof = utils.get_file_path('witness.graphml', temp_dir=False)
            shutil.copy(proof, persistent_proof)

    if stop_event:
        stop_event.set()

    if generator_thread:
        generator_thread.join(timeout=5)

    os.chdir(old_dir)
    print(utils.statistics)
    print("IUV: " + validation_result.verdict.upper())

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
