import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8000"));

export class ApiClientError extends Error {
  constructor({ code, message, details, status }) {
    super(message || "Unexpected API error");
    this.name = "ApiClientError";
    this.code = code || "api_error";
    this.details = details || {};
    this.status = status || null;
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

function toApiClientError(error) {
  if (error instanceof ApiClientError) {
    return error;
  }

  if (axios.isAxiosError(error)) {
    const payload = error.response?.data;
    const serverError = payload?.error;

    return new ApiClientError({
      code: serverError?.code || "request_failed",
      message: serverError?.message || error.message || "Request failed",
      details: serverError?.details || {},
      status: error.response?.status || null,
    });
  }

  return new ApiClientError({
    code: "unknown_error",
    message: error instanceof Error ? error.message : "Unknown error",
    details: {},
    status: null,
  });
}

async function safeRequest(requestFn) {
  try {
    const response = await requestFn();
    return response.data;
  } catch (error) {
    throw toApiClientError(error);
  }
}

export async function apiGetConfig(profile) {
  return safeRequest(() => apiClient.get("/api/config", { params: { profile } }));
}

export async function apiSaveConfig(profile, settings) {
  return safeRequest(() =>
    apiClient.post("/api/config", {
      profile,
      settings,
    })
  );
}

export async function apiGetStatus(profile) {
  return safeRequest(() => apiClient.get("/api/status", { params: { profile } }));
}

export async function apiStartBot(profile) {
  return safeRequest(() =>
    apiClient.post("/api/bot/start", {
      profile,
    })
  );
}

export async function apiStopBot(profile) {
  return safeRequest(() =>
    apiClient.post("/api/bot/stop", {
      profile,
    })
  );
}

export async function apiListProfiles() {
  return safeRequest(() => apiClient.get("/api/profiles"));
}

export async function apiCreateProfile(name, copyFrom) {
  return safeRequest(() =>
    apiClient.post("/api/profiles", { name, copyFrom: copyFrom || null })
  );
}

export async function apiDeleteProfile(name) {
  return safeRequest(() =>
    apiClient.delete("/api/profiles", { params: { name } })
  );
}

export async function apiImportProfile(file) {
  const formData = new FormData();
  formData.append("file", file);
  return safeRequest(() =>
    apiClient.post("/api/profiles/import", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  );
}

export async function apiExportProfile(name) {
  const response = await apiClient.get("/api/profiles/export", {
    params: { name },
    responseType: "blob",
  });
  const blob = new Blob([response.data], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name.endsWith(".ini") ? name : `${name}.ini`;
  a.click();
  URL.revokeObjectURL(url);
  return true;
}

export async function apiGetStats(profile, mode = "session") {
  return safeRequest(() => apiClient.get("/api/stats", { params: { profile, mode } }));
}

export async function apiGetLogs(profile, limit = 50) {
  return safeRequest(() => apiClient.get("/api/logs", { params: { profile, limit } }));
}

export { API_BASE_URL };
