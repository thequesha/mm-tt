import { useState, useCallback } from "react";
import api from "@/lib/api";

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(
    () => !!localStorage.getItem("token")
  );

  const login = useCallback(async (username: string, password: string) => {
    const response = await api.post("/login", { username, password });
    const { access_token } = response.data;
    localStorage.setItem("token", access_token);
    setIsAuthenticated(true);
    return access_token;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setIsAuthenticated(false);
  }, []);

  return { isAuthenticated, login, logout };
}
