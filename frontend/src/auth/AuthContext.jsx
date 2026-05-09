import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Auth, tokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!tokens.access) { setUser(null); setLoading(false); return; }
    try {
      const me = await Auth.me();
      setUser(me);
    } catch {
      tokens.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = async (username, password) => {
    const data = await Auth.login(username, password);
    tokens.set(data.access, data.refresh);
    await refresh();
  };

  const logout = () => {
    tokens.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

export const can = (user, capability) => {
  if (!user) return false;
  if (user.is_superuser) return true;
  switch (capability) {
    case "admin":  return user.role === "admin";
    case "lead":   return ["admin", "lead"].includes(user.role);
    case "write":  return ["admin", "lead", "analyst"].includes(user.role);
    case "view":   return true;
    default:       return false;
  }
};
