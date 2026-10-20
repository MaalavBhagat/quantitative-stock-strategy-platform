from importlib.metadata import version

import quant_research


def test_package_imports_and_has_version():
    assert isinstance(quant_research.__version__, str)
    assert quant_research.__version__ != ""
    # The code's version must match the installed project version in pyproject.toml.
    assert quant_research.__version__ == version("quantitative-stock-strategy-platform")
