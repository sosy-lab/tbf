#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<time.h>
#include<signal.h>
#include<setjmp.h>
#include<math.h>
#include<stdint.h>

#include <sanitizer/coverage_interface.h>

#define MAX_TEST_SIZE 10000
#define MAX_TEST_NUMBER 150000
#define FIXED_SEED 1618033988

#define SUCCESS_STATUS 147

static unsigned int test_size = 0;
static unsigned int test_runs = 0;

static int test_is_new = 0;
static int done = 0;

static char test_vector[MAX_TEST_SIZE + 1][100] = {};

unsigned int get_rand_seed() {
#ifdef FIXED_SEED
  return FIXED_SEED;
#else
  struct timespec curr_time;
  clock_gettime(CLOCK_REALTIME, &curr_time);
  return curr_time.tv_nsec;
#endif
}

void input(void * var, size_t var_size, const char * var_name) {
  int inp_size = var_size * sizeof(char) * 2 + 1;
  char input_val[inp_size];
  unsigned char * new_val = malloc(sizeof(char) * var_size);
  memset(input_val, 0, inp_size);
  for (int i = 0; i < var_size; i++) {
    new_val[var_size - i - 1] = (char) (rand() & 255);
    char * current_pos = &input_val[i*2];
    snprintf(current_pos, 3, "%.2x", new_val[var_size - i - 1]);
  }
  snprintf(test_vector[test_size], 99, "%s: 0x%s", var_name, input_val);
  memcpy(var, new_val, var_size);
  free(new_val);

  test_size++;

  if (test_size >= MAX_TEST_SIZE) {
    fprintf(stderr, "Maximum test vector size of %d reached, aborting.\n", MAX_TEST_SIZE);
    abort();
  }
}


extern int __main(void);
void write_test();
void reset_test_vector();
jmp_buf env;

void abort_handler(int sig) {
  longjmp(env, 1);
}

void exit_handler(int status, void * nullarg) {
  if (done) {
    exit(0);
  } else if (status == SUCCESS_STATUS) {
    write_test();
    exit(0);
  } else {
    on_exit(exit_handler, NULL);
    longjmp(env, 1);
  }
}

void __sanitizer_cov_trace_pc_guard_init(uint32_t *start,
                                                    uint32_t *stop) {
  static uint64_t N;  // Counter for the guards.
  if (start == stop || *start) return;  // Initialize only once.
  for (uint32_t *x = start; x < stop; x++)
    *x = ++N;  // Guards should start from 1.
}

void __sanitizer_cov_trace_pc_guard(uint32_t * guard) {
  if (!*guard) {
    return;
  }

  *guard = 0;
  test_is_new = 1;
}

int main() {
  srand(get_rand_seed());
  signal(SIGABRT, abort_handler);
  on_exit(exit_handler, NULL);

  while (test_runs < MAX_TEST_NUMBER) {
    reset_test_vector();
    if (setjmp(env) == 0) {
      __main();
    }
    if (test_is_new) {
      write_test();
      test_runs++;
    }
  }
  done = 1;
  exit(0);
}

void reset_test_vector() {
  for (int i = 0; i < MAX_TEST_SIZE && test_vector[i][0] != 0; i++) {
    memset(test_vector[i], 0, 1);
  }
  test_size = 0;
  test_is_new = 0;
}

void write_test() {
  unsigned int digits_needed = log10(test_runs+1) + 1;
  // 11 characters for vector.test, 1 for \0
  char vector_name[11+1+digits_needed];
  sprintf(vector_name, "vector%u.test", test_runs);
  FILE *vector = fopen("tmp_vector", "w");
  for (int i = 0; test_vector[i][0] != '\0'; i++) {
      fprintf(vector, "%s\n", test_vector[i]);
  }
  fclose(vector);
  rename("tmp_vector", vector_name);
}
