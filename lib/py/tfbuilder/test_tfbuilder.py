# tfbuilder is a module for easy creation of test-format XML files.
# This file is part of tfbuilder.
#
# Copyright (C) 2018  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for tfbuilder module."""

import datetime
from lxml import etree
from nose.tools import raises
from nose.tools import ok_
import tfbuilder as tf
from tfbuilder import architecture
from tfbuilder import specs

PARSER = etree.XMLParser(dtd_validation=True)
"""XML parser used in unit tests."""
TEST_FILE = 'test/test.c'
"""Dummy test file used in unit tests."""
DATE = datetime.datetime.min
"""Dummy date used in unit tests."""


def test_metadatabuilder_none_arguments():
    """Test that MetadataBuilder does not allow None for its required arguments."""
    valid_args = ("C", "Human v1.5", specs.STATEMENT_COVERAGE, TEST_FILE,
                  "main", architecture.LINUX32, DATE)
    none_args = [None] * len(valid_args)
    args = list(zip(valid_args, none_args))
    # check for each argument to builder, that a TypeError is thrown if it is None
    for i in range(0, len(valid_args)):
        curr_args = [x[1] if i == idx else x[0] for idx, x in enumerate(args)]
        assert len(valid_args) == len(curr_args)
        try:
            tf.MetadataBuilder(*curr_args)
            ok_(False)
        except TypeError:
            pass  # expected, continue


def test_metadatabuilder_empty_arguments():
    """Test that MetadataBuilder does not allow an empty string for its required arguments."""
    valid_args = ("C", "Human v1.5", specs.STATEMENT_COVERAGE, TEST_FILE,
                  "main", architecture.LINUX32, DATE)
    empty_args = [""] * len(valid_args)
    args = list(zip(valid_args, empty_args))
    # check for each argument to builder, that a TypeError is thrown if it is None
    for i in range(0, len(valid_args)):
        curr_args = [x[1] if i == idx else x[0] for idx, x in enumerate(args)]
        assert len(valid_args) == len(curr_args)
        try:
            tf.MetadataBuilder(
                *[x[1] if i == idx else x[0] for idx, x in enumerate(args)])
            ok_(False)
        except ValueError:
            pass  # expected, continue


def test_metadata_builder():
    """Test that a metadata builder with valid args is built successfully."""
    builder = tf.MetadataBuilder(
        "C",
        "Human v1.5",
        specs.STATEMENT_COVERAGE,
        TEST_FILE,
        "main",
        architecture.LINUX32,
        creation_time=DATE)

    _check_build_valid(builder)

@raises(AttributeError)
def test_testcasebuilder_empty():
    """Test that building from TestcaseBuilder without a testcase raises an error."""
    builder = tf.TestcaseBuilder()
    builder.build()


def test_testcasebuilder_input():
    """Test that test input values are accepted in different formats."""
    for inp in ("5", 5, "Multiline\nString", b"ByteString",
                "\\x00\\x50\\x10\\x40"):
        yield _check_testcasebuilder_input, inp


def _check_testcasebuilder_input(inp):
    builder = tf.TestcaseBuilder()
    builder.test_case_start() \
        .input_val(inp)

    _check_build_valid(builder)


def test_testcasebuilder_input_attributes():
    """Test that the attributes of test input values can be set to different values."""
    builder = tf.TestcaseBuilder()
    builder.test_case_start() \
        .input_val("17", variable="xy", value_type="char *") \
        .input_val("15", variable="y") \
        .input_val("1395", value_type="unsigned char")

    _check_build_valid(builder)

def test_testcasebuilder_coverserror():
    """Test that a test case with coversError=true is built successfully."""
    builder = tf.TestcaseBuilder()
    builder.test_case_start(covers_error=True)

    _check_build_valid(builder)


def _check_build_valid(builder):
    created_xml = builder.build()

    etree.fromstring(created_xml, PARSER)
