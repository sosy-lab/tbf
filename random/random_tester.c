#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<time.h>

unsigned int get_rand_seed() {
  struct timespec curr_time;
  clock_gettime(CLOCK_REALTIME, &curr_time);
  return curr_time.tv_nsec;
}

void input(void * var, size_t var_size, const char * var_name) {
  srand(get_rand_seed());
  FILE *vector = fopen("vector.txt", "a+");
  size_t int_size = sizeof(int);
  unsigned char * new_val = malloc(var_size);

  fprintf(vector, "%s: 0x", var_name);
  for (int i = 0; i < var_size; i++) {
    new_val[var_size - i] = (char) (rand() & 255);
    fprintf(vector, "%.2x", new_val[var_size - i]);
  }
  memcpy(new_val, var, var_size);

  fprintf(vector, "\n");
  fclose(vector);
}
