// Autenticação persistente. Guarda o token no keychain/keystore (expo-secure-store) —
// sobrevive a restart. No demo, qualquer token vale (FakeAuthProvider no BFF); em produção,
// entra o fluxo Supabase (magic link/OAuth) e o BFF valida o JWT (S11).
import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "charutei.token";

type AuthState = {
  token: string | null;
  loading: boolean; // true enquanto lê o token persistido no boot
  signIn: (token: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    SecureStore.getItemAsync(TOKEN_KEY)
      .then((t) => setToken(t))
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  async function signIn(next: string) {
    await SecureStore.setItemAsync(TOKEN_KEY, next);
    setToken(next);
  }

  async function signOut() {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  return ctx;
}

// Token garantido (para hooks que só rodam autenticados). Lança se ausente.
export function useToken(): string {
  const { token } = useAuth();
  if (!token) throw new Error("sem token — rota autenticada acessada sem sessão");
  return token;
}
