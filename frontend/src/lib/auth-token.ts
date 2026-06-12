let tokenGetter: (() => Promise<string | null>) | null = null;

export function registerAuthTokenGetter(getter: () => Promise<string | null>) {
  tokenGetter = getter;
}

export async function getAuthToken(): Promise<string | null> {
  if (!tokenGetter) {
    return null;
  }
  return tokenGetter();
}
