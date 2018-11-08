import tbf.utils as utils
import nose.tools as n

method_name = '__VERIFIER_nondet_int'
bool_method_name = '__VERIFIER_nondet_bool'

test_values = [
    (b'\x00\x00\x00\x00', 0),
    (b'\x01\x01\x01\x01', 16843009),
    (b'\xff\xff\xff\x7f', 2147483647),
    (b'\x00', 0),
    (b'\x01', 1),
]

nondet_methods = [{
    'name': method_name,
    'type': 'int',
    'params': []
}, {
    'name': bool_method_name,
    'type': '_Bool',
    'params': []
}]


def test_multicharacter_conversion():
    for input, expected in test_values:
        yield _check_conversion, input, expected


def _check_conversion(input_value, expected_value):
    actual, = utils.convert_to_int(input_value, method_name, nondet_methods)
    n.eq_(actual, expected_value)
