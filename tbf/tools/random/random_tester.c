#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<time.h>

int requires_seed = 1;

unsigned int get_rand_seed() {
  struct timespec curr_time;
  clock_gettime(CLOCK_REALTIME, &curr_time);
  return curr_time.tv_nsec;
}

void input(void * var, size_t var_size, const char * var_name) {
  if (requires_seed) {
    srand(get_rand_seed());
    requires_seed = 0;
  }
  FILE *vector = fopen("vector.test", "a+");
  size_t int_size = sizeof(int);
  unsigned char * new_val = malloc(var_size);

  fprintf(vector, "%s: 0x", var_name);
  for (int i = 0; i < var_size; i++) {
    new_val[var_size - i - 1] = (char) (rand() & 255);
    fprintf(vector, "%.2x", new_val[var_size - i - 1]);
  }
  memcpy(var, new_val, var_size);

  fprintf(vector, "\n");
  fclose(vector);
}
