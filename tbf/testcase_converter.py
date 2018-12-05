from abc import ABCMeta, abstractmethod

import lib.py.tfbuilder as tfbuilder
import datetime

import os

METADATA_FILE = "metadata.xml"


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


class XmlWritingTestConverter:
    """A test converter that writes testcase XML files for each retrieved test vector."""

    def __init__(self, delegate, output_directory='.'):
        """Create new XmlWritingTestConverter

        :param TestConverter delegate: delegate test converter
        :param str output_directory: directory that XMLs are written to.
        """
        self.delegate = delegate
        self.output_directory = os.path.abspath(output_directory)

    def _get_test_cases_in_dir(self, directory=None, exclude=None):
        return self.delegate._get_test_cases_in_dir(directory, exclude)

    def _get_test_case_from_file(self, test_file):
        return self.delegate._get_test_case_from_file(test_file)

    def get_test_vector(self, test_case):
        test_vector = self.delegate.get_test_vector(test_case)
        write_testvector(test_vector, self.output_directory, force_write=True)
        return test_vector

    def get_test_vectors(self, directory, exclude=None):
        vectors = self.delegate.get_test_vectors(directory, exclude)
        for v in vectors:
            write_testvector(v, self.output_directory, force_write=True)
        return vectors


def write_metadata(program, producer, specification, architecture, start_time=None, directory='.'):
    """Writes a metadata XML file for a test suite with the given information.

    If no start time is given, the current time is taken.

    :param str program: path to the program under test.
    :param str producer: the producer of the test suite.
    :param str specification: the specification the test suite aims at.
    :param str architecture: the system architecture the tests were created for.
        Example: Linux 32bit.
    :param datetime.datetime start_time: the creation time of the test suite.
    """
    if start_time is None:
        start_time = datetime.datetime.now()
    metadata_xml = tfbuilder.MetadataBuilder(
        "C",
        producer,
        specification,
        program,
        "main",
        architecture,
        start_time
    ).build()

    if not os.path.exists(directory):
        os.mkdir(directory)

    with open(os.path.join(directory, METADATA_FILE), 'bw+') as outp:
        outp.write(metadata_xml)


def write_testvector(test_vector, directory='.', force_write=False):
    """Write a testcase XML for the given test vector.

    :param utils.TestVector test_vector: the test vector to write the test case XML for.
    :param str directory: the directory to write the resulting XML into.
    :param bool force_write: whether to overwrite an existing file.
    :raises ValueError: if force_write=False and the filename of the resulting XML already exists.
    """
    builder = tfbuilder.TestcaseBuilder().test_case_start()
    for element in test_vector.vector:
        builder.input_val(element['value'])
    testcase_xml = builder.build()

    if not os.path.exists(directory):
        os.mkdir(directory)

    unique_name = test_vector.name
    output_name = os.path.join(directory, unique_name + ".xml")
    if os.path.exists(output_name) and not force_write:
        raise ValueError("XML file with name of test vector already exists: %s" % output_name)
    with open(output_name, 'bw+') as outp:
        outp.write(testcase_xml)
