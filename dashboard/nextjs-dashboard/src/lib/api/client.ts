import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    const origin = new URL(API_BASE_URL);
    const target = new URL(config.url || "/", config.baseURL || API_BASE_URL);
    if (target.origin !== origin.origin || target.username || target.password ||
        (origin.protocol !== "https:" && !(origin.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname)))) {
      throw new Error("A project credential can only be sent to its configured protected service.");
    }
    // Add auth token if available
    if (typeof window !== "undefined") {
      const token = sessionStorage.getItem("auth_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Missing or expired scoped credentials require a new login.
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("auth_token");
        window.location.replace(new URL("/login", window.location.origin).href);
      }
    }
    return Promise.reject(error);
  }
);
