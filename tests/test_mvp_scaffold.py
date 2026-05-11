from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mvp_monorepo_scaffold_files_exist():
    expected_paths = [
        ROOT / "apps" / "web" / "package.json",
        ROOT / "apps" / "web" / "src" / "app" / "page.tsx",
        ROOT / "services" / "api" / "pyproject.toml",
        ROOT / "services" / "api" / "src" / "sadify_api" / "main.py",
    ]

    missing = [
        str(path.relative_to(ROOT))
        for path in expected_paths
        if not path.exists()
    ]

    assert missing == []
