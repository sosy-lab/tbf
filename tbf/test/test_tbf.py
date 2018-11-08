import io
import nose.tools as n
from contextlib import redirect_stdout

from os import path

import tbf

timelimit_per_test = 10

class TestTbf(object):
    tools = ["afl", "cpatiger", "crest", "fshell", "klee", "random"]
    machine_models = ["-32", "-64"]

    @classmethod
    def setUpClass(cls):
        tbf_root = path.dirname(tbf.__file__)
        global true_filename
        true_filename = path.join(tbf_root, "test", "programs", "simple_true.c")
        global false_filename
        false_filename = path.join(tbf_root, "test", "programs", "simple_false.c")

        if not path.exists(true_filename):
            raise AssertionError("File does not exist: " + true_filename)

        if not path.exists(false_filename):
            raise AssertionError("File does not exist: " + false_filename)

    def _create_stop_event(self):
        return tbf.StopEvent()

    def test_false(self):
        for tool in self.tools:
            for machine_model in self.machine_models:
                yield self._test_tool_false, tool, machine_model

    """
    def test_cpatiger_true_32bit(self):
        self._test_tool_true("cpatiger", "-32")

    def test_cpatiger_true_64bit(self):
        self._test_tool_true("cpatiger", "-64")

    def test_crest_true_32bit(self):
        self._test_tool_true("crest", "-32")

    def test_crest_true_64bit(self):
        self._test_tool_true("crest", "-64")

    def test_fshell_true_32bit(self):
        self._test_tool_true("fshell", "-32")

    def test_fshell_true_64bit(self):
        self._test_tool_true("fshell", "-64")

    def test_klee_true_32bit(self):
        self._test_tool_true("klee", "-32")

    def test_klee_true_64bit(self):
        self._test_tool_true("klee", "-64")

    """

    def _test_tool_false(self, tool, machine_model, validation_mode="--execution"):
        result_output = self._run_tool(tool, machine_model, validation_mode, false_filename)

        self.assertResultIsFalse(result_output)

    def _test_tool_true(self, tool, machine_model, validation_mode="--execution"):
        result_output = self._run_tool(tool, machine_model, validation_mode, true_filename)

        self.assertResultIsUnknown(result_output)

    def _run_tool(self, tool, machine_model, validation_mode, filename):
        # Run will not consider timelimit, but only ig-timelimit.
        argv = ["--verbose", "--no-parallel", "--ig-timelimit", str(timelimit_per_test), "-i", tool, validation_mode, machine_model, filename]
        args = tbf._parse_cli_args(argv)
        result_output = TestTbf._run_tbf_and_return_stdout(args, self._create_stop_event())

        print(result_output)
        return result_output

    def assertResultIsFalse(self, tool_output):
        n.eq_(TestTbf._get_result(tool_output), tbf.utils.FALSE)

    def assertResultIsUnknown(self, tool_output):
        n.eq_(TestTbf._get_result(tool_output), tbf.utils.UNKNOWN)

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
