export type AuthenticatedUser = {
  uid: string;
  email: string | null;
  display_name: string | null;
  provider: string;
};

export type AuthSessionResponse = {
  status: "authenticated";
  user: AuthenticatedUser;
};

export async function verifyAuthSession(idToken: string): Promise<AuthSessionResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_SADIFY_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/auth/session`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  });

  if (!response.ok) {
    throw new Error("Backend could not verify this session.");
  }

  return response.json();
}
