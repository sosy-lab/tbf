import os
import nose.tools as n
import tbf.utils as utils

VECTOR_FILE = 'vector.test'

module_dir = os.path.dirname(__file__)


def setUp():
    old_dir = os.path.abspath('.')
    try:
        os.chdir(module_dir)

        utils.execute("make")
        print_inputs = utils.get_executable("./print_inputs")
        check_inputs = utils.get_executable("./check_inputs")

        n.assert_is_not_none(print_inputs)
        n.assert_is_not_none(check_inputs)
    finally:
        os.chdir(old_dir)


def test_generation_and_parsing_consistent():
    print_inputs = utils.get_executable(os.path.join(module_dir, "print_inputs"))
    check_inputs = utils.get_executable(os.path.join(module_dir, "check_inputs"))

    if os.path.exists(VECTOR_FILE):
        os.remove(VECTOR_FILE)
    input_result = utils.execute(print_inputs, quiet=True)
    expected = input_result.stdout
    with open(VECTOR_FILE, 'r') as inp:
        created_values = "\n".join(l.split(":")[1].strip() for l in inp.readlines())

    parse_result = utils.execute(check_inputs, input_str=created_values, quiet=True)
    actual = parse_result.stdout

    n.assert_equal(expected, actual)
