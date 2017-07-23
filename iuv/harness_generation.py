import utils


class HarnessCreator(object):

    def __get_vector_read_method(self):
        return """char * read_bytes(size_t type_size, char * __inp_var) {
    size_t input_length = strlen(__inp_var)-1;
    __inp_var[input_length] = '\\0'; // Remove '\\n' at end
    __inp_var = __inp_var + 2; // Remove "0x" at start
    input_length -= 2;

    if (input_length % 2 > 0) {
        fprintf(stderr, "Input bytes not full bytes: %s\\n", __inp_var);
        abort();
    }
    unsigned char * __value = malloc(type_size);
    char * curr_pos_inp;
    unsigned char * curr_pos_val;
    unsigned int curr_inp_idx = input_length;
    unsigned int curr_val_idx = -1;
    while (curr_inp_idx > 0) {
        curr_inp_idx = curr_inp_idx - 2;
        curr_pos_inp = __inp_var + curr_inp_idx;
        curr_val_idx = curr_val_idx + 1;
        curr_pos_val = __value + curr_val_idx;
        sscanf(curr_pos_inp, "%2hhx", curr_pos_val);
    }

    return __value;
}\n\n"""

    def __init__(self):
        self.repr_type = "__repr"

    def _get_preamble(self):
        preamble = ''
        preamble += "struct _IO_FILE;\ntypedef struct _IO_FILE FILE;\n"
        preamble += "extern struct _IO_FILE *stdin;\n"
        preamble += "extern struct _IO_FILE *stderr;\n"
        preamble += "typedef long unsigned int size_t;\n"
        preamble += "extern void abort (void) __attribute__ ((__nothrow__ , __leaf__))\n"
        preamble += "    __attribute__ ((__noreturn__));\n"
        preamble += "extern void exit (int __status) __attribute__ ((__nothrow__ , __leaf__))\n"
        preamble += "     __attribute__ ((__noreturn__));\n"
        preamble += "extern char *fgets (char *__restrict __s, int __n, FILE *__restrict __stream);\n"
        preamble += "extern int sscanf (const char *__restrict __s,\n"
        preamble += "    const char *__restrict __format, ...) __attribute__ ((__nothrow__ , __leaf__));\n"
        preamble += "extern size_t strlen (const char *__s)\n"
        preamble += "    __attribute__ ((__nothrow__ , __leaf__))\n"
        preamble += "    __attribute__ ((__pure__)) __attribute__ ((__nonnull__ (1)));\n"
        preamble += "extern int fprintf (FILE *__restrict __stream,\n"
        preamble += "    const char *__restrict __format, ...);\n"
        preamble += "extern void *malloc (size_t __size) __attribute__ ((__nothrow__ , __leaf__))\n"
        preamble += "    __attribute__ ((__malloc__));\n"
        preamble += "\n"
        preamble += utils.get_assume_method() + "\n"
        preamble += self.__get_vector_read_method()
        return preamble

    def _get_error_definition(self, method_name):
        definition = 'void {0}() {{\n    exit({1});\n}}\n\n'.format(method_name, utils.error_return)
        return definition

    def _get_nondet_method_definitions(self, nondet_methods, test_vector):
        definitions = ''
        if test_vector is not None:
            definitions += 'unsigned int access_counter = 0;\n\n'
        for method in nondet_methods:
            definitions += utils.get_method_head(method['name'], method['type'], method['params'])
            definitions += ' {\n'
            if method['type'] != 'void':
                definitions += "    size_t type_size = sizeof({0});\n".format(method['type'])
                definitions += "    size_t inp_size = type_size * 2 + 4;\n"
                definitions += "    char * inp_var = malloc(inp_size);\n"
                if test_vector is None:  # Build generic harness
                    definitions += "    fgets(inp_var, inp_size, stdin);\n"
                else:
                    definitions += "    switch(access_counter) {\n"
                    for idx, item in enumerate(test_vector.vector):
                        definitions += "        case {0}: strcpy(inp_var, \"{1}\\n\"); break;\n".format(idx, item['value'])
                    definitions += "        default: abort();\n"
                    definitions += "    }\n"
                    definitions += "    access_counter++;\n"

                definitions += "    return *(({0} *) read_bytes(type_size, inp_var));\n".format(method['type'])
            definitions += '}\n\n'
        return definitions

    def _get_format_specifier(self, method_type):
        return '%*s: ' + utils.get_format_specifier(method_type)

    def create_harness(self, nondet_methods, error_method, test_vector=None):
        harness = ''
        harness += self._get_preamble()
        harness += self._get_error_definition(error_method)
        harness += self._get_nondet_method_definitions(nondet_methods, test_vector)

        return harness