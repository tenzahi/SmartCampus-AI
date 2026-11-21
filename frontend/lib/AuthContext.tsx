"use client";
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type AuthContextType = {
  token: string | null;
  loginUser: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);

  // Au chargement, on regarde si un token est déjà stocké
  useEffect(() => {
    const savedToken = localStorage.getItem('jwt_token');
    if (savedToken) setToken(savedToken);
  }, []);

  const loginUser = (newToken: string) => {
    setToken(newToken);
    localStorage.setItem('jwt_token', newToken); // On sauvegarde dans le navigateur
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('jwt_token');
  };

  return (
    <AuthContext.Provider value={{ token, loginUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé dans un AuthProvider");
  return context;
};