all:
	$(MAKE) -C backend

clean:
	$(MAKE) -C backend clean

test: test-client test-golden

test-client:
	PYTHONPATH=febe python3 febe/tests/test_client.py

test-golden:
	PYTHONPATH=febe python3 febe/generate_golden.py

.PHONY: all clean test test-client test-golden
