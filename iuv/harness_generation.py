import utils


class HarnessCreator(object):

    def _get_vector_read_method(self):
        return b"""char * read_bytes(char * __inp_var) {
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
        preamble += "struct _IO_FILE;\ntypedef struct _IO_FILE FILE;\n"
        preamble += "extern struct _IO_FILE *stdin;\n"
        preamble += "extern struct _IO_FILE *stderr;\n"
        # preamble += "typedef long unsigned int size_t;\n"
        # preamble += "extern void abort (void) __attribute__ ((__nothrow__ , __leaf__))\n"
        # preamble += "    __attribute__ ((__noreturn__));\n"
        # preamble += "extern void exit (int __status) __attribute__ ((__nothrow__ , __leaf__))\n"
        # preamble += "     __attribute__ ((__noreturn__));\n"
        # preamble += "extern char *fgets (char *__restrict __s, int __n, FILE *__restrict __stream);\n"
        # preamble += "extern int sscanf (const char *__restrict __s,\n"
        # preamble += "    const char *__restrict __format, ...) __attribute__ ((__nothrow__ , __leaf__));\n"
        # preamble += "extern size_t strlen (const char *__s)\n"
        # preamble += "    __attribute__ ((__nothrow__ , __leaf__))\n"
        # preamble += "    __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));\n"
        # preamble += "extern int fprintf (FILE *__restrict __stream,\n"
        # preamble += "    const char *__restrict __format, ...);\n"
        # preamble += "extern void *malloc (size_t __size) __attribute__ ((__nothrow__ , __leaf__))\n"
        # preamble += "    __attribute__ ((__malloc__));\n"
        # preamble += "\n"
        preamble += utils.get_assume_method() + "\n"
        preamble = preamble.encode()
        preamble += self._get_vector_read_method()
        return preamble

    def _get_error_definition(self, method_name):
        definition = 'void {0}() {{\n'.format(method_name)
        definition += '    fprintf(stderr, \"{0}\\n\");\n'.format(utils.error_string)
        definition += '    exit(42);\n}\n\n'
        return definition.encode()

    def _get_nondet_method_definitions(self, nondet_methods, test_vector):
        definitions = b''
        if test_vector is not None:
            definitions += b'unsigned int access_counter = 0;\n\n'
        for method in nondet_methods:
            definitions += utils.get_method_head(method['name'], method['type'], method['params']).encode()
            definitions += b' {\n'
            if method['type'] != 'void':
                definitions += "    unsigned int inp_size = 3000;\n".encode()
                definitions += "    char * inp_var = malloc(inp_size);\n".encode()
                if test_vector is None:  # Build generic harness
                    definitions += "    fgets(inp_var, inp_size, stdin);\n".encode()
                else:
                    definitions += "    switch(access_counter) {\n".encode()
                    for idx, item in enumerate(test_vector.vector):
                        if type(item['value']) is bytes:
                            value = item['value']
                        else:
                            value = item['value'].encode()
                        definitions += b''.join([b'case ', str(idx).encode(), b': strcpy(inp_var, "', value, b'"); break;\n'])
                    definitions += b"        default: abort();\n"
                    definitions += b"    }\n"
                    definitions += b"    access_counter++;\n"

                definitions += b''.join([b'    return *((', method['type'].encode(), b' *) read_bytes(inp_var));\n'])
            definitions += b'}\n\n'
        return definitions

    def create_harness(self, nondet_methods, error_method, test_vector=None):
        harness = b''
        harness += self._get_preamble()
        harness += self._get_error_definition(error_method)
        harness += self._get_nondet_method_definitions(nondet_methods, test_vector)

        return harness