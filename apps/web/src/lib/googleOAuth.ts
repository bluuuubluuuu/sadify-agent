const DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file";
const GIS_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

type CodeResponse = {
  code?: string;
  error?: string;
};

type CodeClient = {
  requestCode: () => void;
};

declare global {
  interface Window {
    google?: {
      accounts?: {
        oauth2?: {
          initCodeClient: (config: {
            client_id: string;
            scope: string;
            ux_mode: "popup";
            callback: (response: CodeResponse) => void;
          }) => CodeClient;
        };
      };
    };
  }
}

let googleIdentityScript: Promise<void> | null = null;

export function getGoogleOAuthClientId() {
  return process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID ?? "";
}

export function isGoogleOAuthConfigured() {
  return Boolean(getGoogleOAuthClientId());
}

export async function requestDriveAuthorizationCode(): Promise<string> {
  const clientId = getGoogleOAuthClientId();
  if (!clientId) {
    throw new Error("Configuration needed for Google Drive OAuth.");
  }

  await loadGoogleIdentityScript();
  const initCodeClient = window.google?.accounts?.oauth2?.initCodeClient;
  if (!initCodeClient) {
    throw new Error("Google OAuth client did not load.");
  }

  return new Promise((resolve, reject) => {
    const client = initCodeClient({
      client_id: clientId,
      scope: DRIVE_FILE_SCOPE,
      ux_mode: "popup",
      callback: (response) => {
        if (response.error) {
          reject(new Error(response.error));
          return;
        }
        if (!response.code) {
          reject(new Error("Google Drive did not return an authorization code."));
          return;
        }
        resolve(response.code);
      },
    });
    client.requestCode();
  });
}

function loadGoogleIdentityScript() {
  if (googleIdentityScript) {
    return googleIdentityScript;
  }

  googleIdentityScript = new Promise((resolve, reject) => {
    if (window.google?.accounts?.oauth2) {
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = GIS_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Google OAuth script failed to load."));
    document.head.appendChild(script);
  });

  return googleIdentityScript;
}
