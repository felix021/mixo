all:
	gcc -fPIC -shared -o xor.so xor.c

clean:
	rm xor.so
