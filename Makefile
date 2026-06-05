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
