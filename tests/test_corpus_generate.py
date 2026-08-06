"""Corpus generator expected-hit contract (#140a)."""

import importlib.util
import json
import sys
from pathlib import Path

_GENERATE_PATH = Path(__file__).resolve().parents[1] / "tools" / "corpus" / "generate.py"


def _load_generate():
    spec = importlib.util.spec_from_file_location("corpus_generate", _GENERATE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["corpus_generate"] = mod
    spec.loader.exec_module(mod)
    return mod


corpus_gen = _load_generate()


def test_generate_writes_structured_expectations(tmp_path: Path):
    out = tmp_path / "corpus"
    manifest = corpus_gen.generate(out, seed=42, clean=True)

    assert manifest["version"] == 2
    assert manifest["milestone"] == "v1.1.0"
    assert (out / "manifest.json").is_file()
    assert (out / "Documents" / "Shopping List.txt").is_file()
    assert (out / "Documents" / "vacation-italy.md").is_file()

    shopping = (out / "Documents" / "Shopping List.txt").read_text(encoding="utf-8")
    assert "sourdough" in shopping.casefold()

    expected = manifest["expected_search"]
    assert isinstance(expected["invoice"], dict)
    assert "Documents/invoice.pdf" in expected["invoice"]["must_include"]
    assert expected["sourdough"]["must_include"] == ["Documents/Shopping List.txt"]
    assert expected["sourdough"]["mode"] == "classic"
    assert expected["Italian seaside trip notes"]["mode"] == "semantic"
    assert expected["Italian seaside trip notes"]["must_include"] == [
        "Documents/vacation-italy.md"
    ]

    rag = manifest["expected_rag"]
    assert "What groceries are on the shopping list?" in rag
    assert rag["What groceries are on the shopping list?"]["must_include"] == [
        "Documents/Shopping List.txt"
    ]

    again = corpus_gen.generate(out, seed=42, clean=True)
    assert [f["path"] for f in again["files"]] == [f["path"] for f in manifest["files"]]
    assert again["expected_search"] == manifest["expected_search"]

    disk = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert disk["expected_search"]["chipotle peppers"]["must_include"] == [
        "Documents/Recipes.txt"
    ]
