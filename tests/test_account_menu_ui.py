from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"


def _read(relative_path: str) -> str:
    path = WEB / relative_path
    assert path.exists(), f"missing frontend source: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_account_menu_has_distinct_guest_sign_in_state():
    source = _read("components/shell/AccountMenu.tsx")

    assert "const isSignedIn = Boolean(name || email)" in source
    assert "onSignIn" in source
    assert "Sign in with Google" in source
    assert "Sign in</span>" in source
    assert "isSignedIn ?" in source


def test_signed_in_menu_does_not_duplicate_identity_row():
    source = _read("components/shell/AccountMenu.tsx")

    assert "Signed in" not in source
    assert '{name ?? email ?? "Account"}' not in source
    assert "Google Drive" in source
    assert "Sign out" in source


def test_sidebar_and_workspace_wire_account_sign_in():
    sidebar = _read("components/shell/Sidebar.tsx")
    workspace = _read("components/WorkspaceV2.tsx")

    assert "onSignIn" in sidebar
    assert "onSignIn={onSignIn}" in sidebar
    assert "onSignIn={() => void auth.signIn().catch(() => undefined)}" in workspace
