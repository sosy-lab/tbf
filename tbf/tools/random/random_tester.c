#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<time.h>
#include<signal.h>
#include<setjmp.h>

#define MAX_TEST_SIZE 1000
#define FIXED_SEED 1618033988

unsigned int test_size = 0;
unsigned int test_runs = 0;

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
  // 11 characters for vector.test, 1 for \0, 9 for digits
  char vector_name[11+9+1];
  sprintf(vector_name, "vector%u.test", test_runs);
  FILE *vector = fopen(vector_name, "a+");
  unsigned char * new_val = malloc(var_size);

  fprintf(vector, "%s: 0x", var_name);
  for (int i = 0; i < var_size; i++) {
    new_val[var_size - i - 1] = (char) (rand() & 255);
    fprintf(vector, "%.2x", new_val[var_size - i - 1]);
  }
  memcpy(var, new_val, var_size);

  fprintf(vector, "\n");
  fclose(vector);
  test_size++;

  if (test_size > MAX_TEST_SIZE) {
    fprintf(stderr, "Maximum test vector size of %d reached, aborting.\n", MAX_TEST_SIZE);
    abort();
  }
}


extern int main(void);
jmp_buf env;
void abort_handler(int sig) {
  longjmp(env, 1);
}
void exit_handler() {
  longjmp(env, 1);
}

int generator_main() {
  srand(get_rand_seed());
  signal(SIGABRT, abort_handler);

  while (1) {
    atexit(exit_handler);
    if (setjmp(env) == 0) {
      main();
    }
    test_size = 0;
    test_runs++;
  }
  return 0;
  // todo: capture exit and abort from main()
}
