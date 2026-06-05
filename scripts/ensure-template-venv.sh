#!/usr/bin/env bash
#
# ensure-template-venv.sh
#
# Makes the IETF draft template's venv robust across Python environments
# where ensurepip / python3-venv may be missing or broken (common on
# Python 3.12+, minimal containers, and some Ubuntu releases).
#
# This script can be run manually or invoked from the Makefile.
#
# It does not change the semantics of the template — it just ensures the
# venv that lib/venv.mk expects actually has a working pip.

set -euo pipefail

LIBDIR="${LIBDIR:-lib}"
VENV="${LIBDIR}/.venv"
PYTHON="${PYTHON:-python3}"
REQUIREMENTS="${LIBDIR}/requirements.txt"

echo "==> Ensuring IETF template venv at ${VENV} has pip..."

if [[ ! -d "${VENV}" ]]; then
    echo "    Creating fresh venv (without pip)..."
    "${PYTHON}" -m venv --without-pip "${VENV}"
fi

VENV_PYTHON="${VENV}/bin/python"
VENV_PIP="${VENV}/bin/pip"

if [[ ! -x "${VENV_PIP}" ]]; then
    echo "    Bootstrapping pip using get-pip.py (no ensurepip required)..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | "${VENV_PYTHON}"
fi

# Install / upgrade the template's declared requirements
if [[ -f "${REQUIREMENTS}" ]]; then
    echo "    Installing template requirements..."
    "${VENV_PIP}" install --no-warn-script-location -r "${REQUIREMENTS}"
else
    echo "    WARNING: ${REQUIREMENTS} not found"
fi

echo "==> Template venv ready: ${VENV_PYTHON}"
"${VENV_PYTHON}" --version
"${VENV_PIP}" --version
