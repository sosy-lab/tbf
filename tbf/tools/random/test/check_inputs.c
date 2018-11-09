#include<stdio.h>
#include<stdlib.h>
#include<string.h>

#define SIZE 10000


char * parse_inp(char * __inp_var) {
    unsigned int input_length = strlen(__inp_var)-1;
    /* Remove '\n' at end of input */
    if (__inp_var[input_length] == '\n') {
        __inp_var[input_length] = '\0';
    }

    char * parseEnd;
    char * value_pointer = malloc(16);

    unsigned long long intVal = strtoull(__inp_var, &parseEnd, 0);
    if (*parseEnd != 0) {
      long long sintVal = strtoll(__inp_var, &parseEnd, 0);
      if (*parseEnd != 0) {
        long double floatVal = strtold(__inp_var, &parseEnd);
        if (*parseEnd != 0) {
          fprintf(stderr, "Can't parse input: '%s' (failing at '%s')\n", __inp_var, parseEnd);
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
}

int main() {
  int x[SIZE];
  unsigned int inp_size = 3000;
  for (int i = 0; i < SIZE; i++) {
    char * inp_var = malloc(inp_size);
    fgets(inp_var, inp_size, stdin);
    printf("%d\n", *((int *) parse_inp(inp_var)));
  }
}
