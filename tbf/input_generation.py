import tbf.utils as utils
import os
import logging
from abc import ABCMeta, abstractmethod


class BaseInputGenerator(object):
    __metaclass__ = ABCMeta

    var_counter = 0

    @abstractmethod
    def create_input_generation_cmds(self, filename):
        return list()

    @abstractmethod
    def get_name(self):
        return ''

    @abstractmethod
    def get_run_env(self):
        return os.environ

    @abstractmethod
    def get_test_cases(self, exclude=(), directory=None):
        return list()

    @staticmethod
    def failed(result):
        return result.returncode != 0

    def __init__(self, machine_model, log_verbose):
        self.machine_model = machine_model
        self.log_verbose = log_verbose
        self.statistics = utils.Statistics("Input Generator " + self.get_name())

        self.timer_file_access = utils.Stopwatch()
        self.timer_prepare = utils.Stopwatch()
        self.timer_input_gen = utils.Stopwatch()
        self.timer_generator = utils.Stopwatch()

        self.number_generated_tests = utils.Constant()

        self.statistics.add_value('Time for full input generation',
                                  self.timer_input_gen)
        self.statistics.add_value('Time for test-case generator',
                                  self.timer_generator)
        self.statistics.add_value('Time for controlled file accesses',
                                  self.timer_file_access)
        self.statistics.add_value('Time for file preparation',
                                  self.timer_prepare)
        self.statistics.add_value('Number of generated test cases',
                                  self.number_generated_tests)

    @abstractmethod
    def prepare(self, filecontent, nondet_methods_used):
        pass

    def prepare0(self, filecontent):
        content = filecontent
        content = utils.rewrite_cproblems(content)
        nondet_methods_used = utils.get_nondet_methods()
        content += '\n'
        content += 'struct _IO_FILE;\ntypedef struct _IO_FILE FILE;\n'
        content += "extern struct _IO_FILE *stdin;\n"
        content += "extern struct _IO_FILE *stderr;\n"
        if utils.error_method:
            content += self._get_error_method_dummy()
        content += utils.get_assume_method()
        return self.prepare(content, nondet_methods_used)

    def _get_error_method_dummy(self):
        return 'void ' + utils.error_method + '() {{ fprintf(stderr, \"{0}\\n\"); exit(1); }}\n'.format(
            utils.error_string)

    def generate_input(self, filename, stop_flag):
        default_err = "Unknown error"
        self.timer_input_gen.start()
        try:
            file_to_analyze = utils.get_prepared_name(filename, self.get_name())

            self.timer_file_access.start()
            with open(filename, 'r') as outp:
                filecontent = outp.read()
            self.timer_file_access.stop()

            if os.path.exists(file_to_analyze):
                logging.warning(
                    "Prepared file already exists. Not preparing again.")
            else:
                self.timer_prepare.start()
                prepared_content = self.prepare0(filecontent)
                self.timer_file_access.start()
                with open(file_to_analyze, 'w+') as new_file:
                    new_file.write(prepared_content)
                self.timer_file_access.stop()
                self.timer_prepare.stop()

            cmds = self.create_input_generation_cmds(file_to_analyze)
            for cmd in cmds:
                self.timer_generator.start()
                result = utils.execute(
                    cmd,
                    env=self.get_run_env(),
                    quiet=False,
                    err_to_output=True,
                    stop_flag=stop_flag)
                self.timer_generator.stop()
                if BaseInputGenerator.failed(result) \
                        and (not stop_flag or not stop_flag.is_set()):
                    raise utils.InputGenerationError("Failed at command: " +
                                                     ' '.join(cmd))

            return self._get_success_and_stats()

        except utils.CompileError as e:
            logging.error("Compile error in input generation: %s", e.msg if e.msg else default_err)
            return self._get_failed_and_stats()
        except utils.InputGenerationError as e:
            # Should be error because an error in input generation is not expected
            logging.error("Input generation error: %s", e.msg
                          if e.msg else default_err)
            return self._get_failed_and_stats()
        except utils.ParseError as e:
            logging.error("Parse error: %s", e.msg if e.msg else default_err)
            return self._get_failed_and_stats()

        finally:
            self.timer_input_gen.stop()
            for n, s in self.statistics.stats:
                if type(s) is utils.Stopwatch and s.is_running():
                    s.stop()

            self.number_generated_tests.value = len(self.get_test_cases())

    def _get_failed_and_stats(self):
        return False, self.statistics

    def _get_success_and_stats(self):
        return True, self.statistics
