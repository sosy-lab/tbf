import unittest
import tbf.utils as utils

method_name = '__VERIFIER_nondet_int'
bool_method_name = '__VERIFIER_nondet_bool'


class TestUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        utils.undefined_methods = [{
            'name': method_name,
            'type': 'int',
            'params': []
        }, {
            'name': bool_method_name,
            'type': '_Bool',
            'params': []
        }]

    def test_multicharacter_conversion(self):
        value = b'\x00\x00\x00\x00'
        expected = 0
        actual, = utils.convert_to_int(value, method_name)
        self.assertEqual(actual, expected)
        value = b'\x01\x01\x01\x01'
        expected = 16843009
        actual, = utils.convert_to_int(value, method_name)
        self.assertEqual(actual, expected)
        value = b'\xff\xff\xff\x7f'
        expected = 2147483647
        actual, = utils.convert_to_int(value, method_name)
        self.assertEqual(actual, expected)

        value = b'\x00'
        expected = 0
        actual, = utils.convert_to_int(value, bool_method_name)
        self.assertEqual(actual, expected)
        value = b'\x01'
        expected = 1
        actual, = utils.convert_to_int(value, bool_method_name)
        self.assertEqual(actual, expected)
