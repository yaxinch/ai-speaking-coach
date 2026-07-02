const API_BASE_URL = "";

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export interface ApiRequestOptions extends RequestInit {
  suppressUnauthorizedHandler?: boolean;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = "Request failed.";
  try {
    const body = await response.json();
    message = body.detail ?? message;
  } catch {
    message = response.statusText || message;
  }
  return new ApiError(message, response.status);
}

function notifyUnauthorized(response: Response, suppressed: boolean): void {
  if (response.status === 401 && !suppressed) unauthorizedHandler?.();
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { suppressUnauthorizedHandler = false, ...requestOptions } = options;
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers ?? {})
    }
  });

  if (!response.ok) {
    notifyUnauthorized(response, suppressUnauthorizedHandler);
    throw await errorFromResponse(response);
  }

  return response.json() as Promise<T>;
}

export async function apiBlobRequest(path: string, options: ApiRequestOptions = {}): Promise<Blob> {
  const { suppressUnauthorizedHandler = false, ...requestOptions } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) }
  });
  if (!response.ok) {
    notifyUnauthorized(response, suppressUnauthorizedHandler);
    throw await errorFromResponse(response);
  }
  const blob = await response.blob();
  if (!blob.size) throw new Error("The server returned empty audio.");
  return blob;
}

export async function apiEmptyRequest(path: string, options: ApiRequestOptions = {}): Promise<void> {
  const { suppressUnauthorizedHandler = false, ...requestOptions } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...requestOptions, credentials: "include" });
  if (!response.ok) {
    notifyUnauthorized(response, suppressUnauthorizedHandler);
    throw await errorFromResponse(response);
  }
}
