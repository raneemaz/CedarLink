import { createContext, useContext, useState } from "react";

const AuthContext = createContext();

// Read the persisted session synchronously so `user` is already correct on
// the first render — otherwise ProtectedRoute bounces an authenticated user
// to /login on a hard reload before an effect can hydrate the state.
function readStoredUser() {
  const savedUser = localStorage.getItem("user");
  const savedToken = localStorage.getItem("token");

  if (
    !savedUser ||
    savedUser === "undefined" ||
    savedUser === "null" ||
    !savedToken
  ) {
    return null;
  }

  try {
    return JSON.parse(savedUser);
  } catch {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser);

  const login = (userData, token, refreshToken) => {
    if (userData) {
      localStorage.setItem("user", JSON.stringify(userData));
      setUser(userData);
    }

    if (token) {
      localStorage.setItem("token", token);
    }

    if (refreshToken) {
      localStorage.setItem("refresh_token", refreshToken);
    }
  };

  const logout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");

    // Drop the cached display-currency preference so the next user who logs
    // in on this browser never inherits it.
    localStorage.removeItem("cedarlink_currency");

    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}