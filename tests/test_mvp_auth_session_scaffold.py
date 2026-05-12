from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_firebase_auth_frontend_files_exist():
    expected_paths = [
        WEB_SRC / "components" / "AuthPanel.tsx",
        WEB_SRC / "lib" / "api.ts",
        WEB_SRC / "lib" / "firebaseClient.ts",
        WEB_SRC / "lib" / "firebaseConfig.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_firebase_auth_frontend_contract_is_visible_and_persistent():
    workspace_shell = (WEB_SRC / "components" / "WorkspaceShell.tsx").read_text(
        encoding="utf-8"
    )
    auth_panel = (WEB_SRC / "components" / "AuthPanel.tsx").read_text(
        encoding="utf-8"
    )
    firebase_client = (WEB_SRC / "lib" / "firebaseClient.ts").read_text(
        encoding="utf-8"
    )
    firebase_config = (WEB_SRC / "lib" / "firebaseConfig.ts").read_text(
        encoding="utf-8"
    )

    assert "AuthPanel" in workspace_shell
    assert "Continue as guest" in auth_panel
    assert "Sign in with Google" in auth_panel
    assert "Firebase config needed" in auth_panel
    assert "onAuthStateChanged" in auth_panel
    assert "getIdToken" in auth_panel
    assert "browserLocalPersistence" in firebase_client
    assert "setPersistence" in firebase_client
    assert "GoogleAuthProvider" in firebase_client
    assert "signInWithPopup" in firebase_client
    assert "NEXT_PUBLIC_FIREBASE_API_KEY" in firebase_config
    assert "isFirebaseConfigured" in firebase_config
