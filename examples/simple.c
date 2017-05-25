extern int __VERIFIER_nondet_int(void);
extern void __VERIFIER_error();

int main() {
  int x = __VERIFIER_nondet_int();
  int y = x;

  if (__VERIFIER_nondet_int()) {
    x++;
  } else {
    y++;
  }

  if (x > y) {
    __VERIFIER_error();
  }
}
