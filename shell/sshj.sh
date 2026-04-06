# Source this file to make `sshj` available in your shell.
# It prefers .venv/bin/python inside this project if present.

if [ -n "${ZSH_VERSION:-}" ]; then
  _sshj_script_path="${(%):-%x}"
else
  _sshj_script_path="${BASH_SOURCE[0]}"
fi

_sshj_script_dir="$(cd "$(dirname "${_sshj_script_path}")" && pwd -P)"
SSHJ_PROJECT_ROOT="$(cd "${_sshj_script_dir}/.." && pwd -P)"

# Fallback for edge cases where shells report only a basename.
if [ ! -d "${SSHJ_PROJECT_ROOT}/src/sshj" ] && [ -d "$(pwd -P)/src/sshj" ]; then
  SSHJ_PROJECT_ROOT="$(pwd -P)"
fi

unset _sshj_script_path
unset _sshj_script_dir

sshj() {
  local python_bin
  if [ -x "${SSHJ_PROJECT_ROOT}/.venv/bin/python" ]; then
    python_bin="${SSHJ_PROJECT_ROOT}/.venv/bin/python"
  else
    python_bin="$(command -v python3)"
  fi

  if [ -z "${python_bin}" ]; then
    echo "python3 was not found in PATH." >&2
    return 1
  fi

  PYTHONPATH="${SSHJ_PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" "${python_bin}" -m sshj "$@"
}
