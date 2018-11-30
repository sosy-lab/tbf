from abc import abstractmethod, ABCMeta
import tbf.harness_generation as harness_gen
from tbf.testcase_converter import TestConverter
import logging
import tbf.utils as utils
import os
from time import sleep
import re
from tbf.utils import FALSE, UNKNOWN, ERROR

from typing import List, Iterable, Any

valid_validators = ['cpachecker', 'uautomizer', 'cpa-w2t', 'fshell-w2t']


class ValidationConfig(object):

    def __init__(self, args):
        self.machine_model = args.machine_model

        self.use_execution = args.execution_validation

        self.use_klee_replay = False
        if args.klee_replay_validation:
            if args.input_generator != "klee":
                raise utils.ConfigError(
                    "Klee-replay only works with klee as tester")
            else:
                logging.warning(
                    "Klee-replay only supports the machine architecture! Machine model specified not respected."
                )
                self.use_klee_replay = True

        elif not self.use_execution and not self.use_klee_replay:
            logging.info(
                "No validation technique specified. If you want TBF to check whether generated tests"
                " uncover a specification violation, provide one of the following parameters:"
                " --execution, --klee-replay (KLEE only)")

        self.convert_to_int = args.write_integers
        self.naive_verification = args.naive_verification
        self.stop_after_success = args.stop_after_success

        self.measure_coverage = args.report_coverage


class TestValidator(object):

    def __init__(self, validation_config, extractor: TestConverter):
        self._nondet_var_map = None
        self.machine_model = validation_config.machine_model
        self.config = validation_config
        self.harness_creator = harness_gen.HarnessCreator()
        self._extractor = extractor

        self.naive_verification = validation_config.naive_verification

        # If a void appears in a line, there must be something between
        # the void and the __VERIFIER_error() symbol - otherwise
        # it is a function definition/declaration.
        self.error_method_pattern = re.compile(
            '((?!void).)*(void.*\S.*)?__VERIFIER_error\(\) *;.*')

        self.statistics = utils.Statistics('Test Validator ' + self.get_name())
        self.timer_validation = utils.Stopwatch()
        self.statistics.add_value('Time for validation', self.timer_validation)
        self.timer_execution_validation = utils.Stopwatch()
        self.statistics.add_value('Time for execution validation',
                                  self.timer_execution_validation)
        self.counter_size_harnesses = utils.Counter()
        self.statistics.add_value('Total size of harnesses',
                                  self.counter_size_harnesses)

        self.counter_handled_test_cases = utils.Counter()
        self.statistics.add_value('Number of looked-at test cases',
                                  self.counter_handled_test_cases)

        self.final_test_vector_size = utils.Constant()
        self.statistics.add_value("Size of successful test vector",
                                  self.final_test_vector_size)

    def get_error_lines(self, program_file):
        with open(program_file, 'r') as inp:
            content = inp.readlines()

        err_lines = list()
        for line_num, line in enumerate(content, start=1):
            # Try to differentiate definition from call
            # through the 'void' condition
            if self.error_method_pattern.match(line):
                err_lines.append(line_num)
        assert err_lines  # Asser that there is at least one error call
        return err_lines

    def get_name(self):
        return "Test Validator"

    @staticmethod
    def _decide_single_verdict(result, test_origin, test_vector=None):
        if any(r == FALSE for r in result):
            return utils.VerdictFalse(test_origin, test_vector)
        else:
            return utils.VerdictUnknown()

    def decide_final_verdict(self, results):
        """
        Decides the final verdict for the given sequence of verdicts.

        :param results: sequence of Verdicts
        :return: verdict 'false' if any false-verdict exists. Otherwise, verdict 'unknown' if naive verification
                 is not used, and verdict 'true' if naive verification is used
        """
        if any(r.is_positive() for r in results):
            return next(r for r in results if r.is_positive())
        elif not self.naive_verification:
            return utils.VerdictUnknown()
        else:
            return utils.VerdictTrue()

    def create_all_test_vectors(self, new_test_cases, nondet_methods):
        all_vectors = list()
        if len(new_test_cases) > 0:
            logging.info("Looking at %s new test file(s).", len(new_test_cases))
        for test_case in new_test_cases:
            logging.debug('Looking at test case %s .', test_case)
            assert os.path.exists(test_case.origin)
            test_vector = self._extractor.get_test_vector(test_case)
            all_vectors.append(test_vector)
        return all_vectors

    def create_harness(self, test_name, test_vector, error_method, nondet_methods):
        harness = self.harness_creator.create_harness(
            nondet_methods=nondet_methods,
            error_method=error_method,
            test_vector=test_vector)
        harness_file = test_name + '.harness.c'

        return {'name': harness_file, 'content': harness}

    def _perform_validation(self, program_file, validator,
                            is_ready_func, stop_event, tests_directory, error_method, nondet_methods):
        visited_tests = set()
        verdicts = list()
        while not is_ready_func() and not stop_event.is_set():
            new_test_vectors = self._extractor.get_test_vectors(tests_directory, visited_tests)
            next_verdict_list = self._k(program_file, validator, new_test_vectors, error_method, nondet_methods)
            verdicts += next_verdict_list
            if self.config.stop_after_success and any(r.is_positive() for r in next_verdict_list):
                return self.decide_final_verdict(verdicts)
            else:
                new_test_names = [t.name for t in new_test_vectors]
                visited_tests = visited_tests.union(new_test_names)
            sleep(0.001)  # Sleep for 1 millisecond

        if not stop_event.is_set():
            new_test_vectors = self._extractor.get_test_vectors(tests_directory, visited_tests)
            next_verdict_list = self._k(program_file, validator, new_test_vectors, error_method, nondet_methods)
            verdicts += next_verdict_list
        return self.decide_final_verdict(verdicts)

    def perform_klee_replay_validation(self, program_file, is_ready_func,
                                       stop_event, tests_directory, error_method, nondet_methods):
        validator = KleeReplayRunner(self.config.machine_model)
        return self._perform_validation(program_file, validator,
                                        is_ready_func, stop_event,
                                        tests_directory, error_method, nondet_methods)

    def perform_execution_validation(self, program_file, is_ready_func,
                                     stop_event, tests_directory, error_method, nondet_methods):

        if self.config.measure_coverage:
            validator = CoverageMeasuringExecutionRunner(
                self.config.machine_model, self.get_name())
        else:
            validator = ExecutionRunner(self.config.machine_model,
                                        self.get_name())

        try:
            return self._perform_validation(program_file, validator,
                                            is_ready_func, stop_event,
                                            tests_directory, error_method, nondet_methods)
        finally:
            if type(validator) is CoverageMeasuringExecutionRunner:
                lines_ex, branch_ex, branch_taken = validator.get_coverage(
                    program_file)
                if lines_ex:
                    self.statistics.add_value("Statements covered", lines_ex)
                if branch_ex:
                    self.statistics.add_value("Branch conditions executed",
                                              branch_ex)
                if branch_taken:
                    self.statistics.add_value("Branches covered", branch_taken)

    def _k(self, program_file: str, validator: Any, test_vectors: Iterable[utils.TestVector], error_method: str,
           nondet_methods: List[str]) -> Iterable[utils.Verdict]:
        """
        Return the verdicts for the given test vectors.

        :param program_file: the program file to check against
        :param validator: the validator used to check the test cases
        :param test_cases: the sequence of test cases to check
        :param error_method: the error method to check for
        :param nondet_methods: the non-deterministic methods that should be stubbed
        :return: The sequence of verdicts, corresponding to the given test cases.
                 A verdict is 'false' if the test case reaches the error method. It is 'unknown', otherwise.
        """
        results = list()
        for test in test_vectors:
            self.timer_execution_validation.start()
            self.timer_validation.start()
            try:
                next_result = validator.run(program_file, test, error_method, nondet_methods)
                results.append(self._decide_single_verdict(next_result, test.origin, test))
            finally:
                self.timer_execution_validation.stop()
                self.timer_validation.stop()
            self.counter_handled_test_cases.inc()

            logging.debug('Result for %s: %s', test.origin, str(next_result))
            if self.config.stop_after_success and next_result == FALSE:
                self.final_test_vector_size = len(test)
                return results
        return results

    def check_inputs(self,
                     program_file,
                     error_method,
                     nondet_methods,
                     is_ready_func,
                     stop_event,
                     tests_directory=None):
        logging.debug('Checking inputs for file %s', program_file)
        logging.debug('Considering test-case directory: %s', tests_directory)
        result = None

        if self.config.use_klee_replay:
            result = self.perform_klee_replay_validation(
                program_file, is_ready_func, stop_event, tests_directory, error_method, nondet_methods)
            logging.info("Klee-replay validation says: " + str(result))

        if (not result or
                not result.is_positive()) and self.config.use_execution:
            result = self.perform_execution_validation(
                program_file, is_ready_func, stop_event, tests_directory, error_method, nondet_methods)
            logging.info("Execution validation says: " + str(result))

        if result is None:
            return utils.VerdictUnknown(), None

        elif result.is_positive():
            if result.test_vector is None:
                result.test_vector = self._extractor.get_test_vector(result.test)
            if result.harness is None:
                harness = self.create_harness(result.test_vector.origin,
                                              result.test_vector, error_method, nondet_methods)
                with open(harness['name'], 'wb+') as outp:
                    outp.write(harness['content'])

                result.harness = harness['name']

        return result, self.statistics


class ExecutionRunner(object):

    def __init__(self, machine_model, producer_name):
        self.machine_model = machine_model
        self.harness = None
        self.producer = producer_name
        self.harness_generator = harness_gen.HarnessCreator()
        self.harness_file = 'harness.c'

    def _get_compile_cmd(self,
                         program_file,
                         harness_file,
                         output_file,
                         c_version='gnu11'):
        mm_arg = self.machine_model.compile_parameter
        cmd = ['gcc']
        cmd += [
            '-std={}'.format(c_version), mm_arg, '-D__alias__(x)=', '-o',
            output_file, '-include', program_file, harness_file, '-lm'
        ]

        return cmd

    def compile(self, program_file, harness_file, output_file):
        compile_cmd = self._get_compile_cmd(program_file, harness_file,
                                            output_file)
        compile_result = utils.execute(compile_cmd, quiet=False)

        if compile_result.returncode != 0:
            compile_cmd = self._get_compile_cmd(program_file, harness_file,
                                                output_file, 'gnu90')
            compile_result = utils.execute(
                compile_cmd, quiet=False, err_to_output=True)

            if compile_result.returncode != 0:
                raise utils.CompileError(
                    "Compilation failed for harness {}".format(harness_file))

        return output_file

    def _get_run_cmd(self, executable):
        return [executable]

    def get_executable_harness(self, program_file, error_method, nondet_methods):
        if not self.harness:
            self.harness = os.path.abspath(
                self._create_executable_harness(program_file, error_method, nondet_methods))
        return self.harness

    def _create_executable_harness(self, program_file, error_method, nondet_methods):
        harness_content = self.harness_generator.create_harness(
            nondet_methods, error_method)
        with open(self.harness_file, 'wb+') as outp:
            outp.write(harness_content)
        output_file = 'a.out'
        return self.compile(program_file, self.harness_file, output_file)

    def run(self, program_file, test_vector, error_method, nondet_methods):
        executable = self.get_executable_harness(program_file, error_method, nondet_methods)
        input_vector = utils.get_input_vector(test_vector)

        if executable and os.path.exists(executable):
            run_cmd = self._get_run_cmd(executable)
            run_result = utils.execute(
                run_cmd,
                quiet=True,
                err_to_output=False,
                input_str=input_vector,
                timelimit=5)

            if utils.found_err(run_result):
                return [FALSE]
            else:
                return [UNKNOWN]
        else:
            return [ERROR]


class CoverageMeasuringExecutionRunner(ExecutionRunner):

    def _get_compile_cmd(self,
                         program_file,
                         harness_file,
                         output_file,
                         c_version='gnu11'):
        cmd = super()._get_compile_cmd(program_file, harness_file, output_file,
                                       c_version)
        cmd += ['-fprofile-arcs', '-ftest-coverage']

        return cmd

    @staticmethod
    def _get_gcov_val(gcov_line):
        if ':' in gcov_line:
            stat = gcov_line.split(':')[1]
            measure_end = stat.find('of ')
            return stat[:measure_end] + "(" + stat[measure_end:] + ")"
        else:
            return None

    def get_coverage(self, program_file):
        cmd = ['gcov', '-bc', self.harness_file]
        res = utils.execute(cmd, quiet=False, err_to_output=False)
        full_cov = res.stdout.splitlines()

        program_name = os.path.basename(program_file)
        lines_executed = None
        branches_executed = None
        branches_taken = None
        for number, line in enumerate(full_cov):
            if line.startswith('File') and program_name in line:
                lines_executed = self._get_gcov_val(full_cov[number + 1])
                branches_executed = self._get_gcov_val(full_cov[number + 2])
                branches_taken = self._get_gcov_val(full_cov[number + 3])
                break

        return lines_executed, branches_executed, branches_taken


class KleeReplayRunner(object):

    def __init__(self, machine_model):
        self.machine_model = machine_model
        self.executable_name = './a.out'
        self.executable = None
        if os.path.exists(self.executable_name):
            os.remove(self.executable_name)

    def run(self, program_file, test_vector, error_method, nondet_methods):
        from tbf.tools import klee

        klee_prepared_file = utils.get_prepared_name(program_file, klee.name)
        c_version = 'gnu11'
        if not self.executable:
            compile_cmd = ['gcc']
            compile_cmd += [
                '-std={}'.format(c_version), "-L", klee.lib_dir,
                '-D__alias__(x)=', '-o', self.executable_name,
                klee_prepared_file, '-lkleeRuntest', '-lm'
            ]
            result = utils.execute(compile_cmd)
            if result.returncode != 0:
                c_version = 'gnu90'
                compile_cmd = ['gcc']
                compile_cmd += [
                    '-std={}'.format(c_version), "-L", klee.lib_dir,
                    '-D__alias__(x)=', '-o', self.executable_name,
                    klee_prepared_file, '-lkleeRuntest', '-lm'
                ]
            self.executable = self.executable_name

        if not os.path.exists(self.executable_name):
            return [ERROR]

        curr_env = utils.get_env()
        curr_env['KTEST_FILE'] = test_vector.origin

        result = utils.execute(
            [self.executable], env=curr_env, err_to_output=False)

        if utils.found_err(result):
            return [FALSE]
        else:
            return [UNKNOWN]
