"""Tests for the missing-value normalization helper. Pure logic, no I/O."""

import numpy as np
import pandas as pd

from movilidad_foranea.cleaning import normalize_missing


def test_empty_string_becomes_nan():
    df = pd.DataFrame({"a": ["x", ""]})
    out = normalize_missing(df)
    assert out.loc[0, "a"] == "x"
    assert pd.isna(out.loc[1, "a"])


def test_whitespace_only_becomes_nan():
    df = pd.DataFrame({"a": ["   "]})
    assert pd.isna(normalize_missing(df).loc[0, "a"])


def test_na_sentinel_becomes_nan():
    df = pd.DataFrame({"a": ["N/A", "ok"]})
    out = normalize_missing(df)
    assert pd.isna(out.loc[0, "a"])
    assert out.loc[1, "a"] == "ok"


def test_numeric_columns_are_untouched():
    df = pd.DataFrame({"lat": [21.05105, -86.8493]})
    out = normalize_missing(df)
    assert out.loc[0, "lat"] == 21.05105
    assert out.loc[1, "lat"] == -86.8493
