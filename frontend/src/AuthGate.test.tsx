import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthGate } from "./AuthGate";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  unauthorizedHandler: null as (() => void) | null
}));

vi.mock("./api/auth", () => ({
  getCurrentUser: api.getCurrentUser,
  login: api.login,
  logout: api.logout
}));

vi.mock("./api/client", () => ({
  setUnauthorizedHandler: (handler: (() => void) | null) => {
    api.unauthorizedHandler = handler;
  }
}));

describe("AuthGate", () => {
  beforeEach(() => {
    api.getCurrentUser.mockReset();
    api.login.mockReset();
    api.logout.mockReset();
    api.unauthorizedHandler = null;
  });

  it("restores an existing session and returns to login after a business 401", async () => {
    api.getCurrentUser.mockResolvedValue({ authenticated: true, username: "admin" });
    render(<AuthGate colorMode="light" onColorModeChange={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Practice Dashboard" })).toBeInTheDocument();
    act(() => api.unauthorizedHandler?.());
    expect(await screen.findByRole("heading", { name: "AI Speaking Coach" })).toBeInTheDocument();
  });

  it("signs in from the login page without storing credentials", async () => {
    const user = userEvent.setup();
    api.getCurrentUser.mockRejectedValue(new Error("Not authenticated"));
    api.login.mockResolvedValue({ authenticated: true, username: "admin" });
    render(<AuthGate colorMode="light" onColorModeChange={vi.fn()} />);

    await user.type(await screen.findByLabelText(/Username/), "admin");
    await user.type(screen.getByLabelText(/Password/), "secret");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(api.login).toHaveBeenCalledWith("admin", "secret"));
    expect(await screen.findByRole("heading", { name: "Practice Dashboard" })).toBeInTheDocument();
    expect(window.localStorage.getItem("password")).toBeNull();
  });

  it("shows one generic message for rejected credentials", async () => {
    const user = userEvent.setup();
    api.getCurrentUser.mockRejectedValue(new Error("Not authenticated"));
    api.login.mockRejectedValue(new Error("Invalid username or password"));
    render(<AuthGate colorMode="light" onColorModeChange={vi.fn()} />);

    await user.type(await screen.findByLabelText(/Username/), "admin");
    await user.type(screen.getByLabelText(/Password/), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Incorrect username or password.")).toBeInTheDocument();
  });
});
