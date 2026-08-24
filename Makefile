LIBDIR := lib
TEXT_PAGINATION := true

ifeq ($(shell test -x $(LIBDIR)/.venv/bin/pip 2>/dev/null && echo ok),)
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

.PHONY: template-venv
template-venv:
	@./scripts/ensure-template-venv.sh

.PHONY: test
test:
	@python3 -c "import cbor2, pytest" || { echo "Install impl package with test extras first"; exit 1; }
	@python3 -m pytest -q impl

.PHONY: cddl
cddl:
	@command -v cddl >/dev/null || { echo "Install the cddl validator first"; exit 1; }
	@cddl compile-cddl --cddl impl/cpb.cddl

latest:: txt html pdf

draft-perry-dtn-cpb.pdf: draft-perry-dtn-cpb.txt scripts/id-txt-to-pdf.py
	@echo "==> Building $@ (from paginated .txt)"
	@$(LIBDIR)/.venv/bin/python scripts/id-txt-to-pdf.py $< $@
