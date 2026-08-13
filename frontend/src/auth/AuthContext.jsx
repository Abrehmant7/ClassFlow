import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "../api/auth.js";
import { setAuthExpiredHandler } from "../api/client.js";
import AuthContext from "./authContext.js";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  getStoredUser,
  setStoredUser,
  setTokens,
} from "./tokenStorage.js";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser());
  const [status, setStatus] = useState(() =>
    getAccessToken() ? "checking" : "idle",
  );

  const clearAuth = useCallback(() => {
    clearTokens();
    setUser(null);
    setStatus("idle");
  }, []);

  useEffect(() => {
    setAuthExpiredHandler(clearAuth);
    return () => setAuthExpiredHandler(null);
  }, [clearAuth]);

  useEffect(() => {
    if (!getAccessToken()) {
      setStatus("idle");
      return;
    }

    let isMounted = true;

    async function loadUser() {
      try {
        const currentUser = await getCurrentUser();
        if (!isMounted) return;
        setStoredUser(currentUser);
        setUser(currentUser);
      } catch {
        if (!isMounted) return;
        clearAuth();
      } finally {
        if (isMounted) {
          setStatus("idle");
        }
      }
    }

    loadUser();

    return () => {
      isMounted = false;
    };
  }, [clearAuth]);

  const register = useCallback(async (payload) => {
    return registerUser(payload);
  }, []);

  const login = useCallback(async ({ username, password }) => {
    const tokenPair = await loginUser({ username, password });
    setTokens(tokenPair);

    const currentUser = await getCurrentUser();
    setStoredUser(currentUser);
    setUser(currentUser);

    return currentUser;
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();

    try {
      if (refreshToken) {
        await logoutUser(refreshToken);
      }
    } finally {
      clearAuth();
    }
  }, [clearAuth]);

  const value = useMemo(
    () => ({
      user,
      status,
      isAuthenticated: Boolean(user && getAccessToken()),
      register,
      login,
      logout,
    }),
    [user, status, register, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
