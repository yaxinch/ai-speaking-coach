import { apiRequest } from "./client";

export interface AuthenticatedUser {
  authenticated: true;
  username: string;
}

export function login(username: string, password: string): Promise<AuthenticatedUser> {
  return apiRequest("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
    suppressUnauthorizedHandler: true
  });
}

export function getCurrentUser(): Promise<AuthenticatedUser> {
  return apiRequest("/api/auth/me", { suppressUnauthorizedHandler: true });
}

export function logout(): Promise<{ authenticated: false }> {
  return apiRequest("/api/auth/logout", { method: "POST" });
}
