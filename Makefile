all:
	$(MAKE) -C backend

clean:
	$(MAKE) -C backend clean

test: all test-client test-golden

test-client:
	PYTHONPATH=febe python3 febe/tests/test_client.py

test-golden:
	PYTHONPATH=febe python3 febe/generate_golden.py

# Golden test generation
# Usage:
#   make golden                              # C backend, default output
#   make golden BACKEND=/path/to/server      # custom server
#   make golden OUTPUT=/tmp/my-golden        # custom output dir
#   make golden SCENARIO=insert_text         # single scenario
#   make golden-list                         # list all scenarios
GOLDEN_ARGS :=
ifdef BACKEND
GOLDEN_ARGS += --backend $(BACKEND)
endif
ifdef OUTPUT
GOLDEN_ARGS += --output $(OUTPUT)
endif
ifdef SCENARIO
GOLDEN_ARGS += --scenario $(SCENARIO)
endif

golden:
	PYTHONPATH=febe python3 febe/generate_golden.py $(GOLDEN_ARGS)

golden-list:
	PYTHONPATH=febe python3 febe/generate_golden.py --list

# Golden test comparison
# Usage:
#   make compare ACTUAL=/tmp/my-golden                    # compare against reference
#   make compare ACTUAL=/tmp/my-golden VERBOSE=1          # show per-operation diffs
#   make compare ACTUAL=/tmp/my-golden CATEGORY=links     # filter by category
#   make compare REFERENCE=/tmp/other ACTUAL=/tmp/mine    # custom reference
REFERENCE ?= golden
COMPARE_ARGS := --reference $(REFERENCE) --actual $(ACTUAL)
ifdef VERBOSE
COMPARE_ARGS += --verbose
endif
ifdef CATEGORY
COMPARE_ARGS += --category $(CATEGORY)
endif

compare:
ifndef ACTUAL
	$(error ACTUAL is required. Usage: make compare ACTUAL=/tmp/my-golden)
endif
	PYTHONPATH=febe python3 febe/compare_golden.py $(COMPARE_ARGS)

.PHONY: all clean test test-client test-golden golden golden-list compare
