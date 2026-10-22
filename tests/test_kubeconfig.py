from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sshj.kubeconfig import KubeconfigEntry
from sshj.storage import KubeconfigStorage


def test_shell_function_exports_selected_kubeconfig(tmp_path) -> None:
    path = tmp_path / "config with 'quote'.yaml"
    storage_path = tmp_path / "kubeconfigs.json"
    KubeconfigStorage(storage_path).save(
        [KubeconfigEntry("CP-01", str(path)), KubeconfigEntry("DEV", "/tmp/dev.yaml")]
    )

    project_root = Path(__file__).resolve().parents[1]
    command = (
        f'source "{project_root}/shell/sshj.sh"\n'
        'sshj kc cp-01\n'
        'printf "KUBECONFIG=%s\\n" "$KUBECONFIG"\n'
        'sshj kc\n'
    )
    env = os.environ.copy()
    env["SSHJ_KUBECONFIGS"] = str(storage_path)
    env.pop("KUBECONFIG", None)
    result = subprocess.run(
        ["bash", "-c", command],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert f"KUBECONFIG={path}" in result.stdout
    assert f"* CP-01 -> {path}" in result.stdout
    assert f"* CP-01 -> {path}" in result.stderr
    assert "  DEV -> /tmp/dev.yaml" in result.stdout


def test_missing_kubeconfig_does_not_change_shell(tmp_path) -> None:
    storage_path = tmp_path / "kubeconfigs.json"
    KubeconfigStorage(storage_path).save([KubeconfigEntry("CP-01", "/tmp/cp-01.yaml")])
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["SSHJ_KUBECONFIGS"] = str(storage_path)
    env["KUBECONFIG"] = "/tmp/original.yaml"
    result = subprocess.run(
        ["bash", "-c", f'source "{project_root}/shell/sshj.sh"; sshj kc missing; printf "%s" "$KUBECONFIG"'],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.stdout == "/tmp/original.yaml"
    assert "not found" in result.stderr
