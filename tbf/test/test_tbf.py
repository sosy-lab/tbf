import io
import nose.tools as n
from contextlib import redirect_stdout

from os import path

import tbf

timelimit_per_test = 20

MACHINE_MODEL_ARGS = ("-32", "-64")


class TestTbf(object):
    testgeneration_tools = ["afl", "cpatiger", "crest", "fshell", "klee", "random"]
    dummy_tool = "dummy"

    @classmethod
    def setUpClass(cls):
        tbf_root = path.dirname(tbf.__file__)
        global true_filename
        true_filename = path.join(tbf_root, "test", "programs", "simple_true.c")
        global false_filename
        false_filename = path.join(tbf_root, "test", "programs", "simple_false.c")
        global false_arbitrary_names_filename
        false_arbitrary_names_filename = path.join(tbf_root, "test", "programs", "simple_false-arbitrary-names.c")

        if not path.exists(true_filename):
            raise AssertionError("File does not exist: " + true_filename)

        if not path.exists(false_filename):
            raise AssertionError("File does not exist: " + false_filename)

        if not path.exists(false_arbitrary_names_filename):
            raise AssertionError("File does not exist: " + false_filename)

        global validation_mode
        validation_mode = "--execution"

    def _create_stop_event(self):
        return tbf.StopEvent()

    def test_dummy_generator(self):
        for machine_model in MACHINE_MODEL_ARGS:
            for task in (true_filename, false_filename):
                    yield self._test_tool, self.dummy_tool, machine_model, task, self.assertResultIsUnknown
        for machine_model in MACHINE_MODEL_ARGS:
            for task in (true_filename, false_filename):
                    yield self._test_tool, self.dummy_tool, machine_model, task, self.assertResultIsDone, "--no-error-method"

    def test_false_task_result_false(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, false_filename, self.assertResultIsFalse

    def test_false_task_without_coverage_result_false(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, false_filename, self.assertResultIsFalse, "--no-coverage"

    def test_false_task_without_error_method_result_done(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, false_filename, self.assertResultIsDone, "--no-error-method"

    def test_false_task_no_stop_after_success_result_false(self):
        # This method does not test whether test generation actually
        # continues after a test was found, but only that tbf runs with
        # this parameter and gets the correct result
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, false_filename, self.assertResultIsFalse, "--no-stop-after-success"

    def test_false_task_with_methods_not_from_svcomp_no_error_method_result_unknown(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, false_arbitrary_names_filename, self.assertResultIsUnknown

    def test_false_task_with_methods_not_from_svcomp_with_error_method_result_false(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, false_arbitrary_names_filename, self.assertResultIsFalse, "--error-method", "error_method"

    def test_true_task_result_unknown(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, true_filename, self.assertResultIsUnknown

    def test_naive_verification_true_task_result_true(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, true_filename, self.assertResultIsTrue, "--naive-verification"

    def test_svcomp_nondets_only(self):
        for tool in self.testgeneration_tools:
            for machine_model in MACHINE_MODEL_ARGS:
                yield self._test_tool, tool, machine_model, false_filename, self.assertResultIsFalse, "--svcomp-nondets"


    def _test_tool(self, tool, machine_model, task, expect_method, *params):
        result_output = self._run_tool(tool, task, machine_model, validation_mode, *params)

        expect_method(result_output)

    def _run_tool(self, tool, filename, *params):
        # Run will not consider timelimit, but only ig-timelimit.
        argv = ["--no-parallel", "--ig-timelimit", str(timelimit_per_test), "-i", tool]
        argv += params
        argv += [filename]
        args = tbf._parse_cli_args(argv)
        result_output = TestTbf._run_tbf_and_return_stdout(args, self._create_stop_event())

        return result_output

    def assertResultIsFalse(self, tool_output):
        n.eq_(TestTbf._get_result(tool_output), tbf.utils.FALSE)

    def assertResultIsUnknown(self, tool_output):
        n.eq_(TestTbf._get_result(tool_output), tbf.utils.UNKNOWN)

    def assertResultIsTrue(self, tool_output):
        n.eq_(TestTbf._get_result(tool_output), tbf.utils.TRUE)

    def assertResultIsDone(self, tool_output):
        n.eq_(TestTbf._get_result(tool_output), tbf.utils.DONE)

    @staticmethod
    def _get_result(tbf_output):
        result_line = [l for l in tbf_output.split('\n') if "TBF verdict" in l][0]
        result = result_line.split(':')[1].strip()

        return result

    @staticmethod
    def _run_tbf_and_return_stdout(args, stop_event):
        with io.StringIO() as buf, redirect_stdout(buf):
            tbf.run(args, stop_event)
            return buf.getvalue()
