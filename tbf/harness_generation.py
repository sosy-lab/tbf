import tbf.utils as utils


class HarnessCreator(object):

    def _get_vector_read_method(self):
        return b"""char * parse_inp(char * __inp_var) {
    unsigned int input_length = strlen(__inp_var)-1;
    /* Remove '\\n' at end of input */
    if (__inp_var[input_length] == '\\n') {
        __inp_var[input_length] = '\\0';
    }

    char * parseEnd;
    char * value_pointer = malloc(16);

    unsigned long long intVal = strtoull(__inp_var, &parseEnd, 0);
    if (*parseEnd != 0) {
      long long sintVal = strtoll(__inp_var, &parseEnd, 0);
      if (*parseEnd != 0) {
        long double floatVal = strtold(__inp_var, &parseEnd);
        if (*parseEnd != 0) {
          fprintf(stderr, "Can't parse input: '%s' (failing at '%s')\\n", __inp_var, parseEnd);
          abort();

        } else {
          memcpy(value_pointer, &floatVal, 16);
        }
      } else {
        memcpy(value_pointer, &sintVal, 8);
      }
    } else {
      memcpy(value_pointer, &intVal, 8);
    }

    return value_pointer;
}\n\n"""

    def __init__(self):
        self.repr_type = b"__repr"

    def _get_preamble(self):
        preamble = ''
        preamble += utils.EXTERNAL_DECLARATIONS
        preamble += "\n"
        preamble += utils.get_assume_method() + "\n"
        preamble = preamble.encode()
        preamble += self._get_vector_read_method()
        return preamble

    def _get_error_definition(self, method_name):
        definition = 'void {0}() {{\n'.format(method_name)
        definition += '    fprintf(stderr, \"{0}\\n\");\n'.format(
            utils.ERROR_STRING)
        definition += '    exit(1);\n}\n\n'
        return definition.encode()

    def _get_nondet_method_definitions(self, nondet_methods, test_vector):
        definitions = b''
        if test_vector is not None:
            definitions += b'unsigned int access_counter = 0;\n\n'
        for method in nondet_methods:
            definitions += utils.get_method_head(method['name'], method['type'],
                                                 method['params']).encode()
            definitions += b' {\n'
            if method['type'] != 'void':
                definitions += "    unsigned int inp_size = 3000;\n".encode()
                definitions += "    char * inp_var = malloc(inp_size);\n".encode(
                )
                if test_vector is None:  # Build generic harness
                    definitions += "    fgets(inp_var, inp_size, stdin);\n".encode(
                    )
                else:
                    definitions += "    switch(access_counter) {\n".encode()
                    for idx, item in enumerate(test_vector.vector):
                        if type(item['value']) is bytes:
                            value = item['value']
                        else:
                            value = item['value'].encode()
                        # yapf: disable
                        definitions += b''.join([
                            b'case ', str(idx).encode(),
                            b': strcpy(inp_var, "', value, b'"); break;\n'
                        ])
                        # yapf: enable
                    definitions += b"        default: {\n #ifdef TBF_GCOV\n __gcov_flush();\n#endif\nabort();}\n"
                    definitions += b"    }\n"
                    definitions += b"    access_counter++;\n"

                definitions += b''.join([
                    b'    return *((', method['type'].encode(),
                    b' *) parse_inp(inp_var));\n'
                ])
            definitions += b'}\n\n'
        return definitions

    def create_harness(self, nondet_methods, error_method, test_vector=None):
        harness = b''
        harness += self._get_preamble()
        if error_method:
            harness += self._get_error_definition(error_method)
        harness += self._get_nondet_method_definitions(nondet_methods,
                                                       test_vector)

        return harness
