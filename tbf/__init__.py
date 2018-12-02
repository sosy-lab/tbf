#!/usr/bin/python3

import argparse
import logging
import multiprocessing.dummy as mp
import os
import shutil
import sys
from ctypes import c_bool
from multiprocessing.context import TimeoutError
from time import sleep

import tbf.testcase_converter as testcase_converter
import tbf.tools.afl as afl
import tbf.tools.cpatiger as cpatiger
import tbf.tools.crest as crest
import tbf.tools.fshell as fshell
import tbf.tools.klee as klee
import tbf.tools.random_tester as random_tester
import tbf.tools.dummy as dummy
import tbf.utils as utils
from tbf.testcase_processing import ProcessingConfig, ExecutionRunner

__VERSION__ = "0.2-dev"


class StopEvent(object):

    def __init__(self):
        m = mp.Manager()
        self.val = m.Value(c_bool, False)

    def is_set(self):
        return self.val.value

    def set(self):
        self.val.value = True


def _create_cli_arg_parser():
    parser = argparse.ArgumentParser(
        description='An Automatic Test-Case Generation and Execution Framework',
        add_help=False)

    args = parser.add_mutually_exclusive_group()
    run_args = args.add_argument_group()
    input_generator_args = run_args.add_argument_group(
        title="Input generation args",
        description="arguments for input generation")
    input_generator_args.add_argument(
        "--input-generator",
        '-i',
        dest="input_generator",
        action="store",
        required=True,
        choices=['afl', 'fshell', 'klee', 'crest', 'cpatiger', 'random', "dummy"],
        help="input generator to use")

    input_generator_args.add_argument(
        "--use-existing-test-dir",
        dest="existing_tests_dir",
        action="store",
        required=False,
        type=str,
        default=None,
        help=
        "don't create new test cases, but use test cases from the provided directory"
    )

    input_generator_args.add_argument(
        "--ig-timelimit",
        dest="ig_timelimit",
        help="time limit (in s) for input generation.\n" +
             "After this limit, input generation" +
             " stops and analysis is performed\nwith the inputs generated up" +
             " to this point.")
    input_generator_args.add_argument(
        "--no-write-integers",
        dest="write_integers",
        action='store_false',
        default=True,
        help="don't write test vector values as integer values."
             "E.g., klee uses multi-character chars by default."
             "Given this argument, these values are converted to integers.")
    input_generator_args.add_argument(
        "--svcomp-nondets",
        dest="svcomp_nondets_only",
        action="store_true",
        default=False,
        help=
        "only expect methods to be non-deterministic according to sv-comp guidelines"
    )

    validation_args = run_args.add_argument_group('Validation')

    validation_args.add_argument(
        '--execution',
        dest="execution_validation",
        action="store_true",
        default=False,
        help="use test execution to find successful test vector")

    validation_args.add_argument(
        "--klee-replay",
        dest="klee_replay_validation",
        action="store_true",
        default=False,
        help=
        "use klee-replay to execute test cases - only works when using klee.")

    validation_args.add_argument(
        "--naive-verification",
        dest="naive_verification",
        action="store_true",
        default=False,
        help=
        "If no error was found and all test cases were handled, assume that the program under test is safe"
    )

    machine_model_args = run_args.add_mutually_exclusive_group()
    machine_model_args.add_argument(
        '-32',
        dest="machine_model",
        action="store_const",
        const="32bit",
        help="Use 32 bit machine model")
    machine_model_args.add_argument(
        '-64',
        dest="machine_model",
        action="store_const",
        const="64bit",
        help="Use 64 bit machine model")

    run_args.add_argument(
        '--timelimit',
        dest="timelimit",
        action="store",
        default=None,
        help="timelimit to use")

    run_args.add_argument(
        '--verbose',
        '-v',
        dest="log_verbose",
        action='store_true',
        default=False,
        help="print verbose information")

    run_args.add_argument(
        '--no-parallel',
        dest='run_parallel',
        action='store_false',
        default=True,
        help="do not run input generation and tests in parallel")

    run_args.add_argument(
        '--keep-files',
        dest='keep_files',
        action='store_true',
        default=False,
        help=
        "keep all created intermediate files (prepared C files, created inputs, etc.)"
    )

    run_args.add_argument(
        '--no-coverage',
        dest='report_coverage',
        action='store_false',
        default=True,
        help="do not report coverage of the executed test cases")

    run_args.add_argument(
        '--stats',
        dest='print_stats',
        action='store_true',
        default=False,
        help="print statistics on stdout")

    run_args.add_argument(
        '--error-method',
        dest='error_method',
        action='store',
        default='__VERIFIER_error',
        help='name of error method to check for. If not specified, __VERIFIER_error is used'
    )

    run_args.add_argument(
        '--no-error-method',
        dest='use_error_method',
        action='store_false',
        default=True,
        help='tells TBF not to look for a call to an error method, but just run all tests'
    )

    run_args.add_argument(
        '--no-stop-after-success',
        dest="stop_after_success",
        action='store_false',
        default=True,
        help="do not terminate TBF after a test case covering the error method was found"
    )

    run_args.add_argument(
        '--write-xml',
        dest="write_xml",
        action='store_true',
        default=False,
        help="write test-format XML files for created tests"
    )

    run_args.add_argument("file", type=str, help="file to verify")

    args.add_argument(
        "--version", action="version", version='{}'.format(__VERSION__))
    args.add_argument('--help', '-h', action='help')
    return parser


def _parse_cli_args(argv):
    try:
        end_idx = argv.index('--')
        known_args = argv[:end_idx]
        input_gen_args = argv[(end_idx + 1):]
    except ValueError:
        known_args = argv
        input_gen_args = None

    parser = _create_cli_arg_parser()
    args = parser.parse_args(known_args)

    args.ig_options = input_gen_args if input_gen_args else list()

    args.timelimit = int(args.timelimit) if args.timelimit else None
    args.ig_timelimit = int(args.ig_timelimit) if args.ig_timelimit else None
    if not args.machine_model:
        logging.info("No machine model specified. Assuming 32 bit")
        args.machine_model = utils.MACHINE_MODEL_32
    elif '32' in args.machine_model:
        args.machine_model = utils.MACHINE_MODEL_32
    elif '64' in args.machine_model:
        args.machine_model = utils.MACHINE_MODEL_64
    else:
        raise AssertionError("Unhandled machine model arg: " +
                             args.machine_model)

    if args.existing_tests_dir:
        if not os.path.exists(args.existing_tests_dir):
            sys.exit("Directory doesn't exist: " + args.existing_tests_dir)
        else:
            args.existing_tests_dir = os.path.abspath(args.existing_tests_dir)

    args.file = os.path.abspath(args.file)

    return args


def _get_input_generator(args):
    input_generator = args.input_generator.lower()

    if input_generator == 'afl':
        return afl.InputGenerator(args.machine_model, args.log_verbose, args.ig_options)

    elif input_generator == 'fshell':
        return fshell.InputGenerator(args.machine_model, args.log_verbose, args.ig_options)

    elif input_generator == 'klee':
        return klee.InputGenerator(
            args.ig_timelimit,
            args.log_verbose,
            args.ig_options,
            machine_model=args.machine_model)

    elif input_generator == 'crest':
        return crest.InputGenerator(
            args.log_verbose,
            args.ig_options,
            machine_model=args.machine_model)

    elif input_generator == 'cpatiger':
        return cpatiger.InputGenerator(
            args.ig_timelimit,
            args.log_verbose,
            args.ig_options,
            machine_model=args.machine_model)

    elif input_generator == 'random':
        return random_tester.InputGenerator(args.machine_model, args.log_verbose, args.ig_options)

    elif input_generator == "dummy":
        return dummy.InputGenerator(
            args.machine_model,
            args.log_verbose,
            args.ig_options
        )
    else:
        raise utils.ConfigError('Unhandled input generator: ' + input_generator)


def _get_test_processor(args, write_xml):
    generator = args.input_generator.lower()
    processing_config = ProcessingConfig(args)
    if generator == 'afl':
        extractor = afl.AflTestConverter()
    elif generator == "fshell":
        extractor = fshell.FshellTestConverter()
    elif generator == 'klee':
        extractor = klee.KleeTestConverter()
    elif generator == 'crest':
        extractor = crest.CrestTestConverter()
    elif generator == 'cpatiger':
        extractor = cpatiger.CpaTigerTestConverter()
    elif generator == 'random':
        extractor = random_tester.RandomTestConverter()
    elif generator == "dummy":
        extractor = dummy.DummyTestConverter()
    else:
        raise AssertionError('Unhandled validator: ' + generator)

    if write_xml:
        extractor = testcase_converter.XmlWritingTestConverter(extractor)

    return testcase_processing.TestProcessor(processing_config, extractor)


def run(args, stop_all_event=None):
    """
    Runs tbf with the given arguments in the current working directory.
    All created files are put in a directory `created_files`.

    :param args:
    :param stop_all_event:
    :return:
    """
    if args.use_error_method:
        error_method = args.error_method
    else:
        error_method = None
    default_err = "Unknown error"

    processing_result = utils.VerdictUnknown()

    filename = args.file
    processing_stats = None
    generator_stats = None
    old_dir_abs = os.path.abspath('.')
    if args.keep_files:
        created_dir = utils.provide_directory(utils.get_output_path('created_files'))
        work_dir = created_dir
    else:
        work_dir = utils.create_temp()

    try:
        _change_dir(work_dir)
        input_generator = _get_input_generator(args)
        test_processor = _get_test_processor(args, args.write_xml)

        if error_method:
            error_method_exclude = [error_method]
            specification = utils.get_error_spec(error_method)
        else:
            error_method_exclude = None
            specification = utils.get_coverage_spec()

        if args.write_xml:
            testcase_converter.write_metadata(
                filename,
                input_generator.get_name(),
                specification,
                args.machine_model
            )

        nondet_methods = utils.find_nondet_methods(filename, args.svcomp_nondets_only, error_method_exclude)

        assert not stop_all_event.is_set(
        ), "Stop event is already set before starting input generation"

        stop_input_generator_event = StopEvent()
        generator_pool = mp.Pool(processes=1)
        if args.existing_tests_dir is None:
            # Define the methods for running test generation and test processing in parallel/sequentially
            if args.run_parallel and _is_processing_necessary(args):
                generator_function = generator_pool.apply_async

                def get_generation_result(res):
                    return res.get(3)

                def is_ready0(r):
                    return r.ready()
            else:
                generator_function = generator_pool.apply

                def get_generation_result(res):
                    return res

                def is_ready0(r):
                    return True

            if args.ig_timelimit:
                utils.set_stop_timer(args.ig_timelimit, stop_input_generator_event)
            generation_result = generator_function(
                input_generator.generate_input,
                args=(filename, error_method, nondet_methods, stop_input_generator_event))

        else:
            generation_result = None

            def get_generation_result(res):
                return True, None

            def is_ready0(r):
                return True

        # We can't use a def here because we pass this function to a different function,
        # in which the def wouldn't be defined
        is_ready = lambda: is_ready0(generation_result)

        if stop_all_event.is_set():
            stop_input_generator_event.set()
            logging.info("Stop-all event is set, returning from execution")
            return

        processing_result, processing_stats = test_processor.process_inputs(
            filename, error_method, nondet_methods, is_ready, stop_all_event, args.existing_tests_dir)
        stop_input_generator_event.set()
        stop_all_event.set()
        logging.debug("Processing terminated and got results")

        try:
            generation_success, generator_stats = get_generation_result(
                generation_result)
            generation_done = True
        except TimeoutError:
            logging.warning("Couldn't' get result of input generation")
            generation_done = False
            generator_pool.terminate()
        logging.debug("Input generation terminated and got results")

        _change_dir(old_dir_abs)
        if processing_result.is_positive():
            test_name = os.path.basename(processing_result.test_vector.origin)
            persistent_test = utils.get_output_path(test_name)
            shutil.copy(processing_result.test_vector.origin, persistent_test)

            if processing_result.harness is not None:
                persistent_harness = utils.get_output_path('harness.c')
                shutil.copy(processing_result.harness, persistent_harness)

                # Create an ExecutionRunner only for the purpose of
                # compiling the persistent harness
                validator_for_compilation = ExecutionRunner(args.machine_model,
                                                            processing_result.test)
                final_harness_name = utils.get_output_path('a.out')
                validator_for_compilation.compile(filename, persistent_harness, final_harness_name)

        elif not generation_done:
            processing_result = utils.VerdictUnknown()

    except utils.CompileError as e:
        # This is a proper error because the program can't be compiled, so no tests can be executed
        logging.error("Compile error: %s", e.msg if e.msg else default_err)
    except utils.ParseError as e:
        # This is a proper error because even parsing of the program failed, so preparation for the test execution
        # was not possible
        logging.error("Parse error: %s", e.msg if e.msg else default_err)
    except FileNotFoundError as e:
        logging.error("File not found: %s", e.filename)
    finally:
        # In case an exception occurred before we went back to the original directory
        _change_dir(old_dir_abs)

        statistics = ""
        if generator_stats:
            statistics += str(generator_stats)
        if processing_stats:
            if statistics:  # If other statistics are there, add some spacing
                statistics += "\n\n"
            statistics += str(processing_stats)
        verdict_str = "\nTBF verdict: " + processing_result.verdict.upper()
        with open(utils.get_output_path('Statistics.txt'),
                  'w+') as stats:
            stats.write(statistics)
            stats.write('\n')
            stats.write(verdict_str)
            stats.write('\n')

        if args.print_stats:
            print("Statistics:")
            print(statistics)
        print(verdict_str)

        if not args.keep_files:
            shutil.rmtree(work_dir, ignore_errors=True)


def _is_processing_necessary(arguments):
    return arguments.execution_validation or arguments.klee_replay_validation \
           or arguments.write_xml


def _change_dir(directory):
    logging.debug("Changing to directory %s", directory)
    os.chdir(directory)


def main():
    timeout_watch = utils.Stopwatch()
    timeout_watch.start()

    args = _parse_cli_args(sys.argv[1:])

    if args.log_verbose:
        logging.getLogger().setLevel(level=logging.DEBUG)
    else:
        logging.getLogger().setLevel(level=logging.INFO)

    stop_event = StopEvent()
    main_run = mp.Process(target=run, args=(args, stop_event))
    try:
        main_run.start()
        while main_run.is_alive() and (
                not args.timelimit or timeout_watch.curr_s() < args.timelimit):
            sleep(0.1)
    finally:
        timeout_watch.stop()
        if args.timelimit and timeout_watch.sum() >= args.timelimit:
            logging.info("Timelimit reached.\n")
        logging.info("Time taken: " + str(timeout_watch.sum()))
        stop_event.set()
        if main_run.is_alive():
            try:
                main_run.join(5)
            except mp.TimeoutError:
                logging.info("Main run didn't terminate within acceptable limit. Killing it.")
                main_run.terminate()


if __name__ == '__main__':
    if sys.platform.startswith('cygwin'):
        logging.warning(
            "It seems you're running TBF on cygwin - this is not officially supported."
        )
    elif not sys.platform.startswith('linux'):
        sys.exit("TBF currently only runs on Linux - exiting.")

    main()
