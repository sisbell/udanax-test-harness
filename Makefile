all:
	$(MAKE) -C backend

clean:
	$(MAKE) -C backend clean

test:
	cd febe && python3 test_client.py

.PHONY: all clean test
