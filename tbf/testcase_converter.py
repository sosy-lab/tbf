from abc import ABCMeta, abstractmethod


class TestConverter:
    """Class responsible for retrieving created test cases and converting them to test vectors."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def _get_test_cases_in_dir(self, directory=None, exclude=None):
        """Return all test cases in the given directory.

        :param str directory: path to directory.
        :param Iterable[str] exclude: set of tests to exclude, identified by their unique names.
        :return Iterable[utils.TestCase]: set of TestCase objects representing all test cases in the given directory,
            except for the test cases named in argument `exclude`.
        """
        raise NotImplementedError()

    @abstractmethod
    def _get_test_case_from_file(self, test_file):
        """Return the TestCase representation for the given test-case file.

        :param str test_file: Path to the file containing the test case.
        :return utils.TestCase: the TestCase representation of the given test-case file.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_test_vector(self, test_case):
        """Return the TestVector representation for the given test case.

        :param utils.TestCase test_case: test case to convert.
        :return utils.TestVector: TestVector representation of given test case.
        """
        raise NotImplementedError()

    def get_test_vectors(self, directory, exclude=None):
        """Return the test vectors for all test cases in the given directory.

        :param str directory: path to directory. If none, the tester's default directory is used
        :param Iterable[str] exclude: set of tests to exclude, identified by their unique names.
        :return Iterable[utils.TestVector]: set of TestVector objects representing all test cases in the given directory,
            except for the test cases named in argument `exclude`.
        """
        vectors = list()
        test_cases = self._get_test_cases_in_dir(directory, exclude)
        for test in test_cases:
            vectors.append(self.get_test_vector(test))
        return vectors
