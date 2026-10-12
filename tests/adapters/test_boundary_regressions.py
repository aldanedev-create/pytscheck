"""Invalid adapter output must fail before compiler execution or filesystem writes."""

import pytest

from pytscheck import SourceFile, check_project
from pytscheck.adapters.sources import collect_sources
from pytscheck.exceptions import AdapterExtractionError, AdapterProtocolError


class InvalidSources:
    name = "invalid-sources"

    def __init__(self, path):
        self.path = path

    def get_sources(self, project_root):
        return [SourceFile(path=self.path, text="export const x = 1;")]


@pytest.mark.parametrize(
    "path", ["../outside.ts", "/tmp/outside.ts", "C:\\outside.ts", "..\\outside.ts", "bad\x00.ts"]
)
def test_invalid_virtual_path_is_rejected(path, tmp_path):
    with pytest.raises(AdapterProtocolError):
        collect_sources(InvalidSources(path), str(tmp_path))


def test_unexpected_extraction_failure_keeps_taxonomy(tmp_path):
    class Broken:
        name = "broken"

        def get_sources(self, project_root):
            raise ValueError("component extraction failed")

    with pytest.raises(AdapterExtractionError) as raised:
        check_project(tmp_path, adapter=Broken())
    assert isinstance(raised.value.__cause__, ValueError)
