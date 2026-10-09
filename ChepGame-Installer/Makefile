# Standalone CHEPGAME.NET HDD PKG Installer (separate TITLE_ID from Store).
TITLE      := ChepGame Installer
VERSION    := 0.33
TITLE_ID   := CHEP00002
CONTENT_ID := IV0000-CHEP00002_00-CHEPINSTALLER001
TOOLCHAIN  := $(OO_PS4_TOOLCHAIN)
INTDIR     := build
UNAME_S    := $(shell uname -s)
CDIR       := linux
ifeq ($(UNAME_S),Darwin)
CDIR       := macos
endif
CXX        := clang++
LD         := ld.lld
LIBS := -lc -lkernel -lc++ -lSceUserService -lSceSysmodule -lSceAppInstUtil -lSceBgft \
        -lSceSystemService -lSDL2
CXXFLAGS := --target=x86_64-pc-freebsd12-elf -fPIC -funwind-tables -c -DORBIS -D_GNU_SOURCE \
            -isysroot $(TOOLCHAIN) -isystem $(TOOLCHAIN)/include \
            -std=c++11 -isystem $(TOOLCHAIN)/include/c++/v1 -I src
LDFLAGS := -m elf_x86_64 -pie --script $(TOOLCHAIN)/link.x --eh-frame-hdr \
           -L$(TOOLCHAIN)/lib $(LIBS) $(TOOLCHAIN)/lib/crt1.o
SOURCES   := $(wildcard src/*.cpp)
OBJECTS   := $(patsubst src/%.cpp,$(INTDIR)/%.o,$(SOURCES))
MODULE_SRC := $(TOOLCHAIN)/src/modules
MODULES   := sce_module/libSceFios2.prx sce_module/libc.prx
ASSETS    := sce_sys/icon0.png
# Install mode is strict by default: do not quietly ship a non-functional PKG.
# Diagnostic mode MUST omit the module even if assets/libjbc.sprx exists.
DIAGNOSTIC_ONLY ?= 0
ifneq ($(filter $(DIAGNOSTIC_ONLY),0 1),$(DIAGNOSTIC_ONLY))
$(error DIAGNOSTIC_ONLY must be 0 or 1)
endif
ifeq ($(DIAGNOSTIC_ONLY),0)
MODULES += sce_module/libjbc.sprx
endif
PACKAGE_FILES := eboot.bin sce_sys/param.sfo sce_sys/icon0.png sce_sys/about/right.sprx $(MODULES)
.PHONY: all clean check-jbc force-gp4
check-jbc:
ifeq ($(DIAGNOSTIC_ONLY),0)
	@test -s assets/libjbc.sprx || { echo 'ERROR: libjbc.sprx missing. Run python3 fetch_jbc.py or choose DIAGNOSTIC_ONLY=1 (cannot install PKGs).'; exit 1; }
else
	@echo 'DIAGNOSTIC_ONLY=1: excluding libjbc.sprx; package cannot install PKGs.'
endif
force-gp4:
	@:

all: $(CONTENT_ID).pkg
$(INTDIR):
	mkdir -p $@
$(INTDIR)/%.o: src/%.cpp src/glyph_data.inc | $(INTDIR)
	$(CXX) $(CXXFLAGS) -o $@ $<
eboot.bin: $(OBJECTS)
	$(LD) $(OBJECTS) -o $(INTDIR)/ChepGameInstaller.elf $(LDFLAGS)
	$(TOOLCHAIN)/bin/$(CDIR)/create-fself -in=$(INTDIR)/ChepGameInstaller.elf \
	  -out=$(INTDIR)/ChepGameInstaller.oelf --eboot eboot.bin --paid 0x3800000000000011
sce_sys/icon0.png: assets/icon0.png
	mkdir -p sce_sys
	cp $< $@
sce_sys/about/right.sprx:
	mkdir -p sce_sys/about
	cp $(MODULE_SRC)/right.sprx $@
sce_module/libSceFios2.prx:
	mkdir -p sce_module
	cp $(MODULE_SRC)/libSceFios2.prx $@
sce_module/libc.prx:
	mkdir -p sce_module
	cp $(MODULE_SRC)/libc.prx $@
sce_module/libjbc.sprx: assets/libjbc.sprx
	mkdir -p sce_module
	cp $< $@
sce_sys/param.sfo: Makefile
	mkdir -p sce_sys
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_new $@
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ APP_TYPE --type Integer --maxsize 4 --value 1
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ APP_VER --type Utf8 --maxsize 8 --value '$(VERSION)'
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ ATTRIBUTE --type Integer --maxsize 4 --value 0
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ CATEGORY --type Utf8 --maxsize 4 --value 'gd'
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ CONTENT_ID --type Utf8 --maxsize 48 --value '$(CONTENT_ID)'
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ DOWNLOAD_DATA_SIZE --type Integer --maxsize 4 --value 0
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ SYSTEM_VER --type Integer --maxsize 4 --value 0
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ TITLE --type Utf8 --maxsize 128 --value '$(TITLE)'
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ TITLE_ID --type Utf8 --maxsize 12 --value '$(TITLE_ID)'
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core sfo_setentry $@ VERSION --type Utf8 --maxsize 8 --value '$(VERSION)'
pkg.gp4: check-jbc force-gp4 eboot.bin sce_sys/param.sfo $(ASSETS) $(MODULES) sce_sys/about/right.sprx
	$(TOOLCHAIN)/bin/$(CDIR)/create-gp4 -out $@ --content-id=$(CONTENT_ID) --files "$(PACKAGE_FILES)"
$(CONTENT_ID).pkg: pkg.gp4
	$(TOOLCHAIN)/bin/$(CDIR)/PkgTool.Core pkg_build $< .
clean:
	rm -rf $(INTDIR) eboot.bin pkg.gp4 sce_sys sce_module $(CONTENT_ID).pkg
