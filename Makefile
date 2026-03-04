SHELL := /bin/bash

# 日本語の道 — Build System
# Requires: pandoc, tectonic (for PDF)

BUILDDIR := build
ASSETS   := assets

# Detect PDF engine (prefer tectonic, then xelatex, lualatex)
PDF_ENGINE := $(shell which tectonic 2>/dev/null || which xelatex 2>/dev/null || which lualatex 2>/dev/null)

# --- Source file lists (ordered) ---

define stage_sources
front_matter.md \
$(1)/stage_intro.md \
$$(sort $$(wildcard $(1)/ch*.md)) \
$$(sort $$(wildcard $(1)/appendix_*.md))
endef

S1_SOURCES := $(eval _s1 := $(call stage_sources,stage1))$(_s1)
S2_SOURCES := $(eval _s2 := $(call stage_sources,stage2))$(_s2)
S3_SOURCES := $(eval _s3 := $(call stage_sources,stage3))$(_s3)
S4_SOURCES := $(eval _s4 := $(call stage_sources,stage4))$(_s4)
S5_SOURCES := $(eval _s5 := $(call stage_sources,stage5))$(_s5)
S6_SOURCES := $(eval _s6 := $(call stage_sources,stage6))$(_s6)

# Re-expand wildcards
S1_SOURCES := front_matter.md stage1/stage_intro.md $(sort $(wildcard stage1/ch*.md)) $(sort $(wildcard stage1/appendix_*.md))
S2_SOURCES := front_matter.md stage2/stage_intro.md $(sort $(wildcard stage2/ch*.md)) $(sort $(wildcard stage2/appendix_*.md))
S3_SOURCES := front_matter.md stage3/stage_intro.md $(sort $(wildcard stage3/ch*.md)) $(sort $(wildcard stage3/appendix_*.md))
S4_SOURCES := front_matter.md stage4/stage_intro.md $(sort $(wildcard stage4/ch*.md)) $(sort $(wildcard stage4/appendix_*.md))
S5_SOURCES := front_matter.md stage5/stage_intro.md $(sort $(wildcard stage5/ch*.md)) $(sort $(wildcard stage5/appendix_*.md))
S6_SOURCES := front_matter.md stage6/stage_intro.md $(sort $(wildcard stage6/ch*.md)) $(sort $(wildcard stage6/appendix_*.md))

# Pandoc common flags
PANDOC_FLAGS := --standalone --toc --toc-depth=2

# PDF flags for CJK support
# Detect available CJK fonts: prefer Hiragino (macOS), fall back to Noto (Linux/Windows)
CJK_MAIN := $(shell fc-list : family | grep -m1 "Hiragino Mincho ProN" 2>/dev/null)
ifeq ($(CJK_MAIN),)
CJK_MAIN := $(shell fc-list : family | grep -m1 "Noto Serif CJK JP" 2>/dev/null)
endif
ifeq ($(CJK_MAIN),)
CJK_MAIN := Noto Serif CJK JP
endif

CJK_SANS := $(shell fc-list : family | grep -m1 "Hiragino Kaku Gothic ProN" 2>/dev/null)
ifeq ($(CJK_SANS),)
CJK_SANS := $(shell fc-list : family | grep -m1 "Noto Sans CJK JP" 2>/dev/null)
endif
ifeq ($(CJK_SANS),)
CJK_SANS := Noto Sans CJK JP
endif

MONO_FONT := $(shell fc-list : family | grep -m1 "Menlo" 2>/dev/null)
ifeq ($(MONO_FONT),)
MONO_FONT := $(shell fc-list : family | grep -m1 "DejaVu Sans Mono" 2>/dev/null)
endif
ifeq ($(MONO_FONT),)
MONO_FONT := DejaVu Sans Mono
endif

PDF_PANDOC_FLAGS := --pdf-engine=$(PDF_ENGINE) \
	-V mainfont="$(CJK_MAIN)" \
	-V sansfont="$(CJK_SANS)" \
	-V monofont="$(MONO_FONT)" \
	-V CJKmainfont="$(CJK_MAIN)" \
	-V CJKsansfont="$(CJK_SANS)" \
	-V geometry:margin=1in \
	-V fontsize=11pt

# --- Targets ---

STAGES := stage1 stage2 stage3 stage4 stage5 stage6

.PHONY: all clean book serve $(STAGES) \
        $(foreach s,$(STAGES),$(s)-md $(s)-html $(s)-epub $(s)-pdf)

all: stage1 stage2 stage3 stage4 stage5 stage6

# --- mdbook HTML book ---

book: src/SUMMARY.md
	mdbook build
	@echo "Built build/book/"

serve: src/SUMMARY.md
	mdbook serve

src/SUMMARY.md: gen_summary.py $(wildcard stage*/ch*.md) $(wildcard stage*/appendix_*.md) $(wildcard stage*/stage_intro.md)
	python3 gen_summary.py

stage1: stage1-md stage1-html stage1-epub stage1-pdf
stage2: stage2-md stage2-html stage2-epub stage2-pdf
stage3: stage3-md stage3-html stage3-epub stage3-pdf
stage4: stage4-md stage4-html stage4-epub stage4-pdf
stage5: stage5-md stage5-html stage5-epub stage5-pdf
stage6: stage6-md stage6-html stage6-epub stage6-pdf

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

# --- Generic build rules ---

# Stage 1
stage1-md: $(BUILDDIR)
	cat $(S1_SOURCES) > $(BUILDDIR)/stage1.md
	@echo "Built $(BUILDDIR)/stage1.md"

stage1-html: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--embed-resources \
		--metadata title="日本語の道 — Stage 1 (N5)" \
		-o $(BUILDDIR)/stage1.html \
		$(S1_SOURCES)
	@echo "Built $(BUILDDIR)/stage1.html"

stage1-epub: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--metadata title="日本語の道 — Stage 1 (N5)" \
		--metadata author="日本語の道 Project" \
		--metadata lang=ja \
		-o $(BUILDDIR)/stage1.epub \
		$(S1_SOURCES)
	@echo "Built $(BUILDDIR)/stage1.epub"

stage1-pdf: $(BUILDDIR)
ifeq ($(PDF_ENGINE),)
	@echo "No PDF engine found. Install tectonic: brew install tectonic"
	@exit 1
else
	pandoc $(PANDOC_FLAGS) \
		$(PDF_PANDOC_FLAGS) \
		--metadata title="日本語の道 — Stage 1 (N5)" \
		-o $(BUILDDIR)/stage1.pdf \
		$(S1_SOURCES)
	@echo "Built $(BUILDDIR)/stage1.pdf"
endif

# Stage 2
stage2-md: $(BUILDDIR)
	cat $(S2_SOURCES) > $(BUILDDIR)/stage2.md
	@echo "Built $(BUILDDIR)/stage2.md"

stage2-html: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--embed-resources \
		--metadata title="日本語の道 — Stage 2 (N4)" \
		-o $(BUILDDIR)/stage2.html \
		$(S2_SOURCES)
	@echo "Built $(BUILDDIR)/stage2.html"

stage2-epub: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--metadata title="日本語の道 — Stage 2 (N4)" \
		--metadata author="日本語の道 Project" \
		--metadata lang=ja \
		-o $(BUILDDIR)/stage2.epub \
		$(S2_SOURCES)
	@echo "Built $(BUILDDIR)/stage2.epub"

stage2-pdf: $(BUILDDIR)
ifeq ($(PDF_ENGINE),)
	@echo "No PDF engine found. Install tectonic: brew install tectonic"
	@exit 1
else
	pandoc $(PANDOC_FLAGS) \
		$(PDF_PANDOC_FLAGS) \
		--metadata title="日本語の道 — Stage 2 (N4)" \
		-o $(BUILDDIR)/stage2.pdf \
		$(S2_SOURCES)
	@echo "Built $(BUILDDIR)/stage2.pdf"
endif

# Stage 3
stage3-md: $(BUILDDIR)
	cat $(S3_SOURCES) > $(BUILDDIR)/stage3.md
	@echo "Built $(BUILDDIR)/stage3.md"

stage3-html: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--embed-resources \
		--metadata title="日本語の道 — Stage 3 (N3)" \
		-o $(BUILDDIR)/stage3.html \
		$(S3_SOURCES)
	@echo "Built $(BUILDDIR)/stage3.html"

stage3-epub: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--metadata title="日本語の道 — Stage 3 (N3)" \
		--metadata author="日本語の道 Project" \
		--metadata lang=ja \
		-o $(BUILDDIR)/stage3.epub \
		$(S3_SOURCES)
	@echo "Built $(BUILDDIR)/stage3.epub"

stage3-pdf: $(BUILDDIR)
ifeq ($(PDF_ENGINE),)
	@echo "No PDF engine found. Install tectonic: brew install tectonic"
	@exit 1
else
	pandoc $(PANDOC_FLAGS) \
		$(PDF_PANDOC_FLAGS) \
		--metadata title="日本語の道 — Stage 3 (N3)" \
		-o $(BUILDDIR)/stage3.pdf \
		$(S3_SOURCES)
	@echo "Built $(BUILDDIR)/stage3.pdf"
endif

# Stage 4
stage4-md: $(BUILDDIR)
	cat $(S4_SOURCES) > $(BUILDDIR)/stage4.md
	@echo "Built $(BUILDDIR)/stage4.md"

stage4-html: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--embed-resources \
		--metadata title="日本語の道 — Stage 4 (N2)" \
		-o $(BUILDDIR)/stage4.html \
		$(S4_SOURCES)
	@echo "Built $(BUILDDIR)/stage4.html"

stage4-epub: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--metadata title="日本語の道 — Stage 4 (N2)" \
		--metadata author="日本語の道 Project" \
		--metadata lang=ja \
		-o $(BUILDDIR)/stage4.epub \
		$(S4_SOURCES)
	@echo "Built $(BUILDDIR)/stage4.epub"

stage4-pdf: $(BUILDDIR)
ifeq ($(PDF_ENGINE),)
	@echo "No PDF engine found. Install tectonic: brew install tectonic"
	@exit 1
else
	pandoc $(PANDOC_FLAGS) \
		$(PDF_PANDOC_FLAGS) \
		--metadata title="日本語の道 — Stage 4 (N2)" \
		-o $(BUILDDIR)/stage4.pdf \
		$(S4_SOURCES)
	@echo "Built $(BUILDDIR)/stage4.pdf"
endif

# Stage 5
stage5-md: $(BUILDDIR)
	cat $(S5_SOURCES) > $(BUILDDIR)/stage5.md
	@echo "Built $(BUILDDIR)/stage5.md"

stage5-html: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--embed-resources \
		--metadata title="日本語の道 — Stage 5 (N1)" \
		-o $(BUILDDIR)/stage5.html \
		$(S5_SOURCES)
	@echo "Built $(BUILDDIR)/stage5.html"

stage5-epub: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--metadata title="日本語の道 — Stage 5 (N1)" \
		--metadata author="日本語の道 Project" \
		--metadata lang=ja \
		-o $(BUILDDIR)/stage5.epub \
		$(S5_SOURCES)
	@echo "Built $(BUILDDIR)/stage5.epub"

stage5-pdf: $(BUILDDIR)
ifeq ($(PDF_ENGINE),)
	@echo "No PDF engine found. Install tectonic: brew install tectonic"
	@exit 1
else
	pandoc $(PANDOC_FLAGS) \
		$(PDF_PANDOC_FLAGS) \
		--metadata title="日本語の道 — Stage 5 (N1)" \
		-o $(BUILDDIR)/stage5.pdf \
		$(S5_SOURCES)
	@echo "Built $(BUILDDIR)/stage5.pdf"
endif


# Stage 6
stage6-md: $(BUILDDIR)
	cat $(S6_SOURCES) > $(BUILDDIR)/stage6.md
	@echo "Built $(BUILDDIR)/stage6.md"

stage6-html: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--embed-resources \
		--metadata title="日本語の道 — Stage 6 (N1 Mastery)" \
		-o $(BUILDDIR)/stage6.html \
		$(S6_SOURCES)
	@echo "Built $(BUILDDIR)/stage6.html"

stage6-epub: $(BUILDDIR)
	pandoc $(PANDOC_FLAGS) \
		--css=$(ASSETS)/water.css \
		--metadata title="日本語の道 — Stage 6 (N1 Mastery)" \
		--metadata author="日本語の道 Project" \
		--metadata lang=ja \
		-o $(BUILDDIR)/stage6.epub \
		$(S6_SOURCES)
	@echo "Built $(BUILDDIR)/stage6.epub"

stage6-pdf: $(BUILDDIR)
ifeq ($(PDF_ENGINE),)
	@echo "No PDF engine found. Install tectonic: brew install tectonic"
	@exit 1
else
	pandoc $(PANDOC_FLAGS) \
		$(PDF_PANDOC_FLAGS) \
		--metadata title="日本語の道 — Stage 6 (N1 Mastery)" \
		-o $(BUILDDIR)/stage6.pdf \
		$(S6_SOURCES)
	@echo "Built $(BUILDDIR)/stage6.pdf"
endif

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned build directory"
