CC = cc
CFLAGS = -g
LFLAGS = -g

BUILD = build

HEADERS = common.h players.h defs.h tags.h requests.h enf.h wisp.h crum.h \
	xanadu.h coredisk.h ndenf.h alloc.h reap.h queues.h protos.h

COMMON_SRC = alloc.c allocdebug.c bert.c context.c corediskin.c \
	corediskout.c correspond.c credel.c disk.c diskalloc.c do1.c do2.c \
	edit.c entexit.c fns.c genf.c granf1.c granf2.c init.c insert.c \
	insertnd.c makeroom.c multiloaf.c ndcuts.c ndinters.c orglinks.c \
	recombine.c retrie.c spanf1.c spanf2.c split.c sporgl.c task.c \
	test.c tumble.c tumbleari.c usefull.c wisp.c queues.c rcfile.c

COMMON_OBJ = $(addprefix $(BUILD)/,alloc.o allocdebug.o bert.o context.o corediskin.o \
	corediskout.o correspond.o credel.o disk.o diskalloc.o do1.o do2.o \
	edit.o entexit.o fns.o genf.o granf1.o granf2.o init.o insert.o \
	insertnd.o makeroom.o multiloaf.o ndcuts.o ndinters.o orglinks.o \
	recombine.o retrie.o spanf1.o spanf2.o split.o sporgl.o task.o \
	test.o tumble.o tumbleari.o usefull.o wisp.o queues.o rcfile.o)

all: $(BUILD)/xumain $(BUILD)/backend $(BUILD)/backenddaemon

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: %.c $(HEADERS) | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/xumain: $(COMMON_OBJ) $(BUILD)/xumain.o $(BUILD)/get1.o $(BUILD)/get2.o $(BUILD)/put.o
	$(CC) $^ $(LFLAGS) -o $@

$(BUILD)/backend: $(COMMON_OBJ) $(BUILD)/be.o $(BUILD)/get1fe.o $(BUILD)/get2fe.o $(BUILD)/putfe.o
	$(CC) $^ $(LFLAGS) -o $@

$(BUILD)/backenddaemon: $(COMMON_OBJ) $(BUILD)/bed.o $(BUILD)/socketbe.o $(BUILD)/get1fe.o $(BUILD)/get2fe.o $(BUILD)/putfe.o
	$(CC) $^ $(LFLAGS) -o $@

clean:
	rm -rf $(BUILD)

.PHONY: all clean
