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
        counter = 'access_counter'
        definitions += 'unsigned int ' + counter + ' = 0;\n\n'
        for method in nondet_methods:
            definitions += utils.get_method_head(method['name'], method['type'], method['params'])
            definitions += ' {\n'
            if method['type'] != 'void':
                cast = '({0})'.format(method['type'])
                definitions += '    switch(' + counter + ') {\n'
                for num, instantiation in sorted(test_vector.items(), key=lambda x: x[0]):
                    if not instantiation['name'] or instantiation['name'] == method['name']:
                        definitions += ' ' * 8 + 'case ' + num + ': ' + counter + '++; return ' + cast + ' ' + instantiation['value'] + ';\n'
                definitions += ' ' * 8 + 'default: return 1/0;\n'  # Force a program failure
                definitions += '    }\n'
            definitions += '}\n'
        return definitions

    def create_harness(self, producer, filename, test_vector, nondet_methods, error_method):
        #harness = '#include <stdlib.h>\n\n'
        harness = ''
        harness += self._get_preamble()
        harness += self._get_error_definition(error_method)
        harness += self._get_nondet_method_definitions(test_vector, nondet_methods)

        return harness
