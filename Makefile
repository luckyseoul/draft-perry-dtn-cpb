LIBDIR := lib

# --------------------------------------------------------------------
# Robust early bootstrap for the IETF template venv.
#
# We run this *before* including the template because lib/venv.mk will
# try "python3 -m venv" and then rely on ensurepip, which is often
# missing on Python 3.12+, minimal Ubuntu, containers, etc.
#
# This shell fragment runs during makefile parsing and ensures a
# working pip exists in lib/.venv before any template rules execute.
# --------------------------------------------------------------------
ifeq ($(shell test -x $(LIBDIR)/.venv/bin/pip 2>/dev/null && echo ok),)
  $(info [bootstrap] IETF template venv needs repair or creation...)
  $(shell ./scripts/ensure-template-venv.sh >/dev/null 2>&1 || true)
endif

-include $(LIBDIR)/main.mk

$(LIBDIR)/main.mk:
ifneq (,$(shell grep "path *= *$(LIBDIR)" .gitmodules 2>/dev/null))
	git submodule sync
	git submodule update --init
else
ifneq (,$(wildcard $(ID_TEMPLATE_HOME)))
	ln -s "$(ID_TEMPLATE_HOME)" $(LIBDIR)
else
	git clone -q --depth 10 -b main \
	    https://github.com/martinthomson/i-d-template $(LIBDIR)
endif
endif

# The early bootstrap logic above (before the -include) is what makes
# "make" work reliably.  You can also run it explicitly:
#
#     ./scripts/ensure-template-venv.sh
#
# or
#
#     make template-venv
.PHONY: template-venv
template-venv:
	@./scripts/ensure-template-venv.sh

# --------------------------------------------------------------------
# Convenient developer targets
# --------------------------------------------------------------------

.PHONY: test
test:
	@echo "==> Ensuring reference implementation dependencies..."
	@cd impl && python3 -m pip install -q -e '.[test]' 2>/dev/null || pip install -q -e '.[test]'
	@echo "==> CPB reference implementation tests"
	@cd impl && python3 test_cpb.py
	@echo
	@echo "==> Simulator smoke test (--quick)"
	@cd impl && python3 config1_sim.py --quick
	@echo
	@echo "==> All reference implementation tests passed."

# Include PDF in the standard build outputs (txt + html + pdf)
latest:: txt html pdf

# xml2rfc --pdf (weasyprint). Needs Noto Serif + Roboto Mono (xml2rfc-fonts).
# Combined CSS = stock xml2rfc.css + scripts/xml2rfc-pdf.css (no hyphenation).
draft-perry-dtn-cpb.pdf: draft-perry-dtn-cpb.xml scripts/xml2rfc-pdf.css
	@echo "==> Building $@ (pdf via xml2rfc)"
	@python3 -c "import xml2rfc, pathlib; b=pathlib.Path(xml2rfc.__file__).parent/'data'/'xml2rfc.css'; e=pathlib.Path('scripts/xml2rfc-pdf.css'); pathlib.Path('.xml2rfc-pdf-combined.css').write_text(b.read_text(encoding='utf-8')+'\n'+e.read_text(encoding='utf-8'), encoding='utf-8')"
	@$(xml2rfc) --pdf --css .xml2rfc-pdf-combined.css $< -o $@
