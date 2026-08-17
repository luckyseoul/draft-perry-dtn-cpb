LIBDIR := lib
# Paginated .txt (4-line two-column I-D masthead), same as posted drafts.
TEXT_PAGINATION := true

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
	@cd impl && python3 test_config1_policies.py
	@cd impl && python3 test_sim_cpb_bridge.py
	@cd impl && python3 test_draft_consistency.py
	@cd impl && python3 test_paper_battery_numbers.py
	@echo
	@echo "==> Simulator smoke test (--quick)"
	@cd impl && python3 config1_sim.py --quick
	@echo
	@echo "==> All reference implementation tests passed."

# Include PDF in the standard build outputs (txt + html + pdf)
latest:: txt html pdf

# PDF is the paginated Internet-Draft text (same page image as .txt),
# not the six-row xml2rfc/WeasyPrint HTML layout.
draft-perry-dtn-cpb.pdf: draft-perry-dtn-cpb.txt scripts/id-txt-to-pdf.py
	@echo "==> Building $@ (from paginated .txt)"
	@$(LIBDIR)/.venv/bin/python scripts/id-txt-to-pdf.py $< $@
