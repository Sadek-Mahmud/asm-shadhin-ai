# SPDX-License-Identifier: GPL-2.0
# Makefile for compiling eBPF/XDP security filter

CLANG ?= clang
LLVM_STRIP ?= llvm-strip
BPFTOOL ?= bpftool

ARCH := $(shell uname -m | sed 's/x86_64/x86/' | sed 's/aarch64/arm64/')

CFLAGS := -O2 -g -Wall -Werror \
          -target bpf \
          -D__TARGET_ARCH_$(ARCH) \
          -I/usr/include/$(shell uname -m)-linux-gnu \
          -I/usr/include \
          -I.

TARGET := ebpf_filter.o
SOURCE := ebpf_filter.c
HEADERS := ebpf_common.h

all: $(TARGET)

$(TARGET): $(SOURCE) $(HEADERS)
	@echo "[+] Compiling eBPF/XDP filter: $(SOURCE) -> $(TARGET)"
	$(CLANG) $(CFLAGS) -c $(SOURCE) -o $@
	@if command -v $(LLVM_STRIP) >/dev/null 2>&1; then \
		$(LLVM_STRIP) -g $@; \
	fi
	@echo "[✓] eBPF Object successfully built: $(TARGET)"

clean:
	@rm -f $(TARGET)
	@echo "[*] Cleaned eBPF artifacts."

dump: $(TARGET)
	llvm-objdump -S $(TARGET)

.PHONY: all clean dump
