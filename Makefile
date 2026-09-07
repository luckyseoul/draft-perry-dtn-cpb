LIBDIR := lib
# Capture the caller's interpreter before the template prepends its own venv
# to PATH. The codec's pinned dependencies belong to the implementation env.
# Override with: make test CPB_PYTHON=/absolute/path/to/python
CPB_PYTHON := $(or $(CPB_PYTHON),$(shell command -v python3))
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
	@"$(CPB_PYTHON)" -c "from importlib.metadata import version; assert version('cbor2') == '5.9.0', 'cbor2==5.9.0 is required'" || { echo "Install impl/requirements.txt with $(CPB_PYTHON), or set CPB_PYTHON to that environment's interpreter."; exit 1; }
	@echo "==> CPB reference implementation tests"
	@cd impl && "$(CPB_PYTHON)" test_cpb.py
	@cd impl && "$(CPB_PYTHON)" test_config1_policies.py
	@cd impl && "$(CPB_PYTHON)" test_sim_cpb_bridge.py
	@cd impl && "$(CPB_PYTHON)" test_draft_consistency.py
	@echo
	@echo "==> All reference implementation tests passed."

.PHONY: cddl
cddl:
	@command -v cddl >/dev/null || { echo "cddl is required; install a CDDL validator first."; exit 1; }
	@cddl compile-cddl --cddl impl/cpb.cddl

# Include PDF in the standard build outputs (txt + html + pdf)
latest:: txt html pdf

# PDF is the paginated Internet-Draft text (same page image as .txt),
# not the six-row xml2rfc/WeasyPrint HTML layout.
draft-perry-dtn-cpb.pdf: draft-perry-dtn-cpb.txt scripts/id-txt-to-pdf.py
	@echo "==> Building $@ (from paginated .txt)"
	@$(LIBDIR)/.venv/bin/python scripts/id-txt-to-pdf.py $< $@
