from pathlib import Path

from nullcase_retrieval.graph import ImportGraph, module_name


def write(root: Path, rel: str, text: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_module_name_follows_packages_in_src_layout(tmp_path: Path) -> None:
    write(tmp_path, "src/app/__init__.py")
    write(tmp_path, "src/app/core/__init__.py")
    mod = write(tmp_path, "src/app/core/models.py")
    test = write(tmp_path, "tests/test_models.py")
    assert module_name(mod) == "app.core.models"
    assert module_name(tmp_path / "src/app/core/__init__.py") == "app.core"
    assert module_name(test) == "test_models"


def test_resolves_absolute_relative_and_from_imports(tmp_path: Path) -> None:
    write(tmp_path, "app/__init__.py", "from . import util\n")
    write(tmp_path, "app/util.py")
    write(tmp_path, "app/sub/__init__.py")
    write(tmp_path, "app/sub/mod.py", "from ..util import helper\nfrom . import sibling\n")
    write(tmp_path, "tests/test_a.py", "import app.util\nfrom app.sub import mod\n")

    graph = ImportGraph.build(tmp_path)
    by_name = {m.name: m.imports for m in graph.modules}
    assert "app.util" in by_name["app"]
    assert {"app.util", "app.util.helper", "app.sub", "app.sub.sibling"} <= by_name["app.sub.mod"]
    assert {"app.util", "app.sub", "app.sub.mod"} <= by_name["test_a"]


def test_importers_include_submodule_imports_but_not_the_module_itself(tmp_path: Path) -> None:
    write(tmp_path, "app/__init__.py")
    write(tmp_path, "app/util.py", "import app\n")
    write(tmp_path, "tests/test_util.py", "from app.util import x\n")
    write(tmp_path, "tests/test_other.py", "import json\n")

    graph = ImportGraph.build(tmp_path)
    assert [m.name for m in graph.importers_of("app.util")] == ["test_util"]
    assert {m.name for m in graph.importers_of("app")} == {"app.util", "test_util"}


def test_skips_virtualenvs_hidden_dirs_and_unparseable_files(tmp_path: Path) -> None:
    write(tmp_path, ".venv/lib/test_vendored.py", "import app\n")
    write(tmp_path, ".hidden/test_h.py", "import app\n")
    write(tmp_path, "tests/test_broken.py", "def (:\n")
    write(tmp_path, "tests/test_ok.py", "import app\n")

    graph = ImportGraph.build(tmp_path)
    assert [str(m.path) for m in graph.modules] == [str(Path("tests/test_ok.py"))]
