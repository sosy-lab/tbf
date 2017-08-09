import utils
import os
import logging
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

    @abstractmethod
    def get_test_count(self):
        pass

    @staticmethod
    def failed(result):
        return result.returncode < 0

    def __init__(self, timelimit, machine_model):
        self.machine_model = machine_model
        self.timelimit = int(timelimit) if timelimit else 0
        self.statistics = utils.statistics.new('Input Generator ' + self.get_name())

        self.timer_file_access = utils.Stopwatch()
        self.timer_prepare = utils.Stopwatch()
        self.timer_input_gen = utils.Stopwatch()

        self.number_generated_tests = utils.Constant()

        self.statistics.add_value('Time for input generation', self.timer_input_gen)
        self.statistics.add_value('Time for controlled file accesses', self.timer_file_access)
        self.statistics.add_value('Time for file preparation', self.timer_prepare)
        self.statistics.add_value('Number of generated test cases', self.number_generated_tests)

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
        content += self._get_error_method_dummy()
        content += utils.get_assume_method()
        return self.prepare(content, nondet_methods_used)

    def _get_error_method_dummy(self):
        return 'void ' + utils.error_method + '() {{ fprintf(stderr, \"{0}\\n\"); abort(); }}\n'.format(utils.error_string)

    def generate_input(self, filename, stop_flag=None):
        default_err = "Unknown error"
        self.timer_input_gen.start()
        try:
            file_to_analyze = utils.get_prepared_name(filename, self.get_name())

            self.timer_file_access.start()
            with open(filename, 'r') as outp:
                filecontent = outp.read()
            self.timer_file_access.stop()

            if os.path.exists(file_to_analyze):
                logging.warning("Prepared file already exists. Not preparing again.")
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
                result = utils.execute(cmd, env=self.get_run_env(), quiet=True, err_to_output=True, stop_flag=stop_flag, timelimit=self.timelimit)
                if BaseInputGenerator.failed(result) and stop_flag and not stop_flag.is_set():
                    logging.error("Generating input failed at command %s", ' '.join(cmd))
            # May throw an InputGenerationError if no test cases were generated
            try:
                self.number_generated_tests.value = self.get_test_count()
            except utils.InputGenerationError as e:
                logging.warning(e.msg)
            return True

        except utils.CompileError as e:
            logging.error("Compile error: %s", e.msg if e.msg else default_err)
            return False
        except utils.InputGenerationError as e:
            logging.error("Input generation error: %s", e.msg if e.msg else default_err)
            return False
        except utils.ParseError as e:
            logging.error("Parse error: %s", e.msg if e.msg else default_err)
            return False

        finally:
            self.timer_input_gen.stop()
