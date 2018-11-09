#include<stdio.h>

#define SIZE 10000
#define DEBUG 1

extern void input(void *, size_t, const char *);

int main() {
  int x[SIZE];
  for (int i = 0; i < SIZE; i++) {
    input(&(x[i]), sizeof(x[i]), "x");
    printf("%d\n", x[i]);
  }
}
