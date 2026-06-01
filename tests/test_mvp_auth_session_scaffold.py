from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_firebase_auth_frontend_files_exist():
    expected_paths = [
        WEB_SRC / "lib" / "hooks" / "useAuth.ts",
        WEB_SRC / "components" / "shell" / "AccountMenu.tsx",
        WEB_SRC / "lib" / "api.ts",
        WEB_SRC / "lib" / "firebaseClient.ts",
        WEB_SRC / "lib" / "firebaseConfig.ts",
    ]

    missing = [str(path.relative_to(ROOT)) for path in expected_paths if not path.exists()]

    assert missing == []


def test_firebase_auth_frontend_contract_is_visible_and_persistent():
    use_auth = (WEB_SRC / "lib" / "hooks" / "useAuth.ts").read_text(encoding="utf-8")
    account = (WEB_SRC / "components" / "shell" / "AccountMenu.tsx").read_text(encoding="utf-8")
    workspace = (WEB_SRC / "components" / "WorkspaceV2.tsx").read_text(encoding="utf-8")
    firebase_client = (WEB_SRC / "lib" / "firebaseClient.ts").read_text(encoding="utf-8")
    firebase_config = (WEB_SRC / "lib" / "firebaseConfig.ts").read_text(encoding="utf-8")

    assert "useAuth" in workspace
    assert "Sign in with Google" in workspace
    assert "Sign out" in account
    assert "onAuthStateChanged" in use_auth
    assert "getIdToken" in use_auth
    assert "verifyAuthSession" in use_auth
    assert "browserLocalPersistence" in firebase_client
    assert "setPersistence" in firebase_client
    assert "GoogleAuthProvider" in firebase_client
    assert "signInWithPopup" in firebase_client
    assert "NEXT_PUBLIC_FIREBASE_API_KEY" in firebase_config
    assert "isFirebaseConfigured" in firebase_config
