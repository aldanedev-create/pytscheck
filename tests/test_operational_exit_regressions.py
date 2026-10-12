"""Use real executables and the real runner to distinguish failures from diagnostics."""

import os
from pathlib import Path

import pytest

from pytscheck import checker, runner
from pytscheck.exceptions import CompilerExecutionError
from tests.helpers import hide_file, make_fake_tsgo


@pytest.fixture
def executable(bin_platform_dir: Path):
    if os.name == "nt":
        pytest.skip("POSIX executable regression fixtures require a POSIX shell")
    path = bin_platform_dir / "lib" / "tsgo"
    with hide_file(path):
        make_fake_tsgo(path)
        try:
            yield path
        finally:
            path.unlink(missing_ok=True)


@pytest.mark.parametrize("exit_code", [137, 3])
def test_abnormal_exit_with_diagnostic_is_operational(executable, exit_code):
    executable.write_text(
        "#!/bin/sh\nprintf 'input.ts(1,1): error TS2322: mismatch\\n'\nexit "
        + str(exit_code)
        + "\n"
    )
    with pytest.raises(CompilerExecutionError) as raised:
        checker.check_source("const x = 1;")
    assert raised.value.returncode == exit_code
    assert "TS2322" in raised.value.stdout


def test_nonzero_exit_with_only_warning_is_not_success(executable):
    executable.write_text("#!/bin/sh\nprintf 'input.ts(1,1): warning TS9999: warning\\n'\nexit 1\n")
    with pytest.raises(CompilerExecutionError):
        checker.check_source("const x = 1;")


def test_normal_type_error_exit_remains_diagnostic(executable):
    executable.write_text("#!/bin/sh\nprintf 'input.ts(1,1): error TS2322: mismatch\\n'\nexit 1\n")
    result = checker.check_source("const x = 1;")
    assert not result.success
    assert result.errors[0].code == 2322
    assert result.elapsed_seconds > 0
    assert runner.binary_path() == executable


@pytest.mark.parametrize(
    "config",
    [
        '{// comment\n"compilerOptions": {"strict": true}}',
        '{"compilerOptions": {"strict": true,},}',
    ],
)
def test_project_jsonc_still_reaches_real_runner(executable, tmp_path, config):
    executable.write_text("#!/bin/sh\nexit 0\n")
    (tmp_path / "tsconfig.json").write_text(config)
    (tmp_path / "main.ts").write_text("export const x = 1;")
    result = checker.check_project(tmp_path)
    assert result.success
    assert result.elapsed_seconds > 0
