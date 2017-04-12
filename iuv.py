#!/usr/bin/python3

import re
import sys
import logging
import argparse
import os

import klee
import crest
import utils

import threading


logging.basicConfig(level=logging.INFO)

__VERSION__ = 0.1


def _prepare_line(line, module):
    logging.debug("Looking at following line: %s", line)
    new_line = ""
    stmt_candidates = re.split('(;|: )', line)
    for idx, stmt in enumerate(stmt_candidates):
        new_stmt = stmt
        if module.is_verifier_assume(new_stmt):
            new_stmt = module.replace_verifier_assume(new_stmt)
        if module.is_nondet_assignment(new_stmt):
            new_stmt = module.replace_nondet_stmt(new_stmt)
        if module.is_nondet_assume(new_stmt):
            new_stmt = module.replace_nondet_assume(new_stmt)
        if module.is_error(new_stmt):
            new_stmt = module.replace_with_exit(utils.error_return)

        new_line += new_stmt
    return new_line


def prepare(filename, module):
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
    name_new_file = '.'.join(os.path.basename(filename).split('.')[:-1] + [module.get_name(), suffix])

    with open(filename, 'r') as old_file:
        content = old_file.readlines()
    logging.debug("Read file %s", filename)
    new_content = [_prepare_line(line, module) + '\n' for line in content]
    logging.debug("Prepared content")
    logging.debug("Writing to file %s", name_new_file)
    with open(name_new_file, 'w') as new_file:
        new_file.writelines(new_content)

    return name_new_file


def _create_parser():
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


def _parse_args(argv):
    parser = _create_parser()
    return parser.parse_args(argv)


def _get_input_generator_module(args):
    input_generator = args.input_generator.lower()
    if input_generator == 'klee':
        return klee.InputGenerator(args.ig_timelimit, args.log_verbose)
    elif input_generator == 'crest':
        return crest
    else:
        raise AssertionError('Unhandled input generator: ' + input_generator)


def run():
    args = _parse_args(sys.argv[1:])

    filename = args.file
    module = _get_input_generator_module(args)

    file_for_analysis = prepare(filename, module)
    if args.run_parallel:
        stop_event = threading.Event()
        generator_thread = threading.Thread(target=module.generate_input, args=(file_for_analysis, stop_event))
        generator_thread.start()
    else:
        stop_event = None
        generator_thread = None
        module.generate_input(file_for_analysis)

    error_reached = module.check_inputs(file_for_analysis, generator_thread)

    if stop_event:
        stop_event.set()

    if error_reached:
        print("IUV: FALSE")
    else:
        print("IUV: UNKNOWN")

run()
