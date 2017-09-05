#!/usr/bin/python3

import sys
import os
import logging
import argparse

import afl
import cpatiger
import crest
import fshell
import klee
import random_tester
import utils
import shutil

from threading import Event, Thread
from multiprocessing.context import TimeoutError
from time import sleep

from test_validation import ValidationConfig

logging.basicConfig(level=logging.INFO)

__VERSION__ = "0.1-dev"


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
                                      choices=['afl', 'fshell', 'klee', 'crest', 'cpatiger', 'random'],
                                      help="input generator to use"
                                      )

    input_generator_args.add_argument("--strategy", "-s",
                                      dest="strategy",
                                      nargs="+",
                                      help="search heuristics to use"
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
                                      help="don't write test vector values as integer values."
                                           "E.g., klee uses multi-character chars by default."
                                           "Given this argument, these values are converted to integers."
                                      )
    input_generator_args.add_argument("--svcomp-nondets",
                                      dest="svcomp_nondets_only",
                                      action="store_true",
                                      default=False,
                                      help="only expect methods to be non-deterministic according to sv-comp guidelines")

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

    validation_args.add_argument("--klee-replay",
                                 dest="klee_replay_validation",
                                 action="store_true",
                                 default=False,
                                 help="use klee-replay to execute test cases - only works when using klee.")

    validation_args.add_argument("--naive-verification",
                                 dest="naive_verification",
                                 action="store_true",
                                 default=False,
                                 help="If no error was found and all test cases were handled, assume that the program under test is safe"
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

    run_args.add_argument('--timelimit',
                          dest="timelimit",
                          action="store",
                          default=None,
                          help="timelimit to use"
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
    args = parser.parse_args(argv)
    args.timelimit = float(args.timelimit) if args.timelimit else None
    if not args.machine_model:
        logging.warning("No machine model specified. Assuming 32 bit")
        args.machine_model = utils.MACHINE_MODEL_32
    elif '32' in args.machine_model:
        args.machine_model = utils.MACHINE_MODEL_32
    elif '64' in args.machine_model:
        args.machine_model = utils.MACHINE_MODEL_64
    else:
        raise AssertionError("Unhandled machine model arg: " + args.machine_model)
    return args


def _get_input_generator_module(args):
    input_generator = args.input_generator.lower()

    if input_generator == 'afl':
        return afl.InputGenerator(args.ig_timelimit, args.machine_model, args.log_verbose)

    elif input_generator == 'fshell':
        return fshell.InputGenerator(args.ig_timelimit, args.machine_model, args.log_verbose)

    elif input_generator == 'klee':
        if args.strategy:
            return klee.InputGenerator(args.ig_timelimit, args.log_verbose, args.strategy, machine_model=args.machine_model)
        else:
            return klee.InputGenerator(args.ig_timelimit, args.log_verbose, machine_model=args.machine_model)

    elif input_generator == 'crest':
        if args.strategy:
            if len(args.strategy) != 1:
                raise utils.ConfigError("Crest requires exactly one strategy. Given strategies: " + args.strategy)
            return crest.InputGenerator(args.ig_timelimit, args.log_verbose, args.strategy[0], machine_model=args.machine_model)
        else:
            return crest.InputGenerator(args.ig_timelimit, args.log_verbose, machine_model=args.machine_model)

    elif input_generator == 'cpatiger':
        return cpatiger.InputGenerator(args.ig_timelimit, args.log_verbose, machine_model=args.machine_model)

    elif input_generator == 'random':
        return random_tester.InputGenerator(args.ig_timelimit, args.machine_model, args.log_verbose)
    else:
        raise utils.ConfigError('Unhandled input generator: ' + input_generator)


def _get_validator_module(args):
    validator = args.input_generator.lower()
    validation_config = ValidationConfig(args)
    if validator == 'afl':
        return afl.AflTestValidator(validation_config)
    elif validator == "fshell":
        return fshell.FshellTestValidator(validation_config)
    elif validator == 'klee':
        return klee.KleeTestValidator(validation_config)
    elif validator == 'crest':
        return crest.CrestTestValidator(validation_config)
    elif validator == 'cpatiger':
        return cpatiger.CpaTigerTestValidator(validation_config)
    elif validator == 'random':
        return random_tester.RandomTestValidator(validation_config)
    else:
        raise AssertionError('Unhandled validator: ' + validator)


def run(args, stop_all_event=None):
    default_err = "Unknown error"

    validation_result = utils.VerdictUnknown()

    filename = os.path.abspath(args.file)
    inp_module = _get_input_generator_module(args)
    validator_module = _get_validator_module(args)

    if args.run_parallel:
        generator_thread = Thread(target=inp_module.generate_input, args=(filename, stop_all_event))
    else:
        generator_thread = utils.SyncThread(target=inp_module.generate_input, args=(filename, stop_all_event), stop_event=stop_all_event)

    old_dir = os.path.abspath('.')
    try:
        os.chdir(utils.tmp)

        utils.find_nondet_methods(filename, args.svcomp_nondets_only)
        if stop_all_event.is_set():
            return

        generator_thread.start()

        if stop_all_event.is_set():
            return

        validation_result = validator_module.check_inputs(filename, generator_thread, stop_all_event)

        try:
            generator_thread.join(timeout=3)
            generation_done = True
        except TimeoutError:
            generation_done = False

        if validation_result.is_positive():
            test_name = os.path.basename(validation_result.test.origin)
            persistent_test = utils.get_file_path(test_name, temp_dir=False)
            shutil.copy(validation_result.test.origin, persistent_test)
            for proof in validation_result.harness, validation_result.witness:
                if proof is not None:
                    proof_name = os.path.basename(proof)
                    if proof_name.endswith('.harness.c'):
                        persistent_proof = utils.get_file_path('harness.c', temp_dir=False)
                    else:
                        assert proof_name.endswith('.witness.graphml')
                        persistent_proof = utils.get_file_path('witness.graphml', temp_dir=False)
                    shutil.copy(proof, persistent_proof)
        elif not generation_done:
            validation_result = utils.VerdictUnknown()

    except utils.CompileError as e:
        logging.error("Compile error: %s", e.msg if e.msg else default_err)
    except utils.InputGenerationError as e:
        logging.error("Input generation error: %s", e.msg if e.msg else default_err)
    except utils.ParseError as e:
        logging.error("Parse error: %s", e.msg if e.msg else default_err)
    finally:
        os.chdir(old_dir)
        print(inp_module.get_statistics())
        print(validator_module.get_statistics())
        print("\nIUV verdict:", validation_result.verdict.upper())

if __name__ == '__main__':
    timeout_watch = utils.Stopwatch()
    timeout_watch.start()
    args = _parse_cli_args(sys.argv[1:])

    stop_event = Event()
    running_thread = utils.Thread(target=run, args=(args, stop_event))
    try:
        running_thread.start()
        while running_thread.is_alive() and (not args.timelimit or timeout_watch.curr_s() < args.timelimit):
            sleep(0.1)
    finally:
        timeout_watch.stop()
        if args.timelimit and timeout_watch.sum() >= args.timelimit:
            logging.error("Timeout error.\n")
        else:
            logging.info("Time taken: " + str(timeout_watch.sum()))
        stop_event.set()
        try:
            running_thread.join(5)
        except TimeoutError:
            logging.warning("Timeout error when waiting for main thread")

