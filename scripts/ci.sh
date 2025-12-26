#!/usr/bin/env bash
set -euo pipefail

cmd=${1:-all}

run_lint() {
  python -m ruff check .
}

run_typecheck() {
  python -m mypy src
}

run_test() {
  python -m pytest
}

run_run() {
  python -m cinetcg
}

case "$cmd" in
  lint) run_lint ;;
  typecheck) run_typecheck ;;
  test) run_test ;;
  run) run_run ;;
  all)
    run_lint
    run_typecheck
    run_test
    ;;
  *)
    echo "Usage: scripts/ci.sh {lint|typecheck|test|run|all}" >&2
    exit 2
    ;;
esac
