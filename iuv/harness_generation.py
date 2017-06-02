import utils


class HarnessCreator(object):

    def __init__(self):
        pass

    def _get_preamble(self):
        preamble = utils.get_assume_method()
        return preamble

    def _get_error_definition(self, method_name):
        definition = 'void {0}() {{\n    exit({1});\n}}\n'.format(method_name, utils.error_return)
        return definition

    def _get_nondet_method_definitions(self, test_vector, nondet_methods):
        definitions = ''
        concrete_values = len([s for s in test_vector.values() if s['name']]) == len(test_vector.values())
        counter = 'access_counter'
        if not concrete_values:
            definitions += 'unsigned int ' + counter + ' = 0;\n\n'
        for method in nondet_methods:
            method_type = utils.get_return_type(method)
            definitions += method_type + ' ' + method + '() {\n'
            if concrete_values:
                definitions += '    static unsigned int ' + counter + '= 0;\n'
            definitions += '    ' + counter + '++;\n'
            definitions += '    switch(' + counter + ') {\n'
            for num, instantiation in sorted(test_vector.items(), key=lambda x: x[0]):
                definitions += ' ' * 8 + 'case ' + num + ': return ' + instantiation['value'] + ';\n'
            definitions += '    }\n}\n'
        return definitions

    def create_harness(self, producer, filename, test_vector, nondet_methods, error_method):
        harness = '#include <stdlib.h>\n\n'
        harness += self._get_preamble()
        harness += self._get_error_definition(error_method)
        harness += self._get_nondet_method_definitions(test_vector, nondet_methods)

        return harness
