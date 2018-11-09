all: build test

build: print_inputs check_inputs

print_inputs: ../random_tester.c print_inputs.c
	$(CC) $(CFLAGS) $(CPPFLAGS) -o print_inputs -include ../random_tester.c print_inputs.c

check_inputs: check_inputs.c
	$(CC) $(CFLAGS) $(CPPFLAGS) -o check_inputs check_inputs.c

test: clean-vector build
	./print_inputs > /tmp/expected.txt
	cut -d":" -f 2 vector.test | tr -d " " > /tmp/vector.test.tmp
	./check_inputs < /tmp/vector.test.tmp > /tmp/actual.txt
	diff -q /tmp/expected.txt /tmp/actual.txt

clean: clean-vector
	rm -f print_inputs \
		check_inputs

clean-vector:
	rm -f vector.test
