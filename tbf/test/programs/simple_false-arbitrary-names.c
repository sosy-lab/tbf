extern int nondet_int(void);
extern char __VERIFIER_nondet_char();
unsigned int possiblyLargeValue(void);
extern void error_method(void);

int main() {
  int x = nondet_int();
  int y = x + __VERIFIER_nondet_char();

  if (possiblyLargeValue()) {
    x++;
  } else {
    y++;
  }

  if (x > y) {
    error_method();
  }

  if (x < y) {
    if (x > 0) {
      y++;
    }
  }

  if (x > y) {
    if (x == 0) {
      y++;
    }
  }
}
