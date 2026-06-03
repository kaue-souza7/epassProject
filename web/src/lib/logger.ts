type LogLevel = "info" | "warn" | "error";

interface LogPayload {
  message: string;
  data?: unknown;
  timestamp: string;
  level: LogLevel;
}

function log(level: LogLevel, message: string, data?: unknown) {
  const payload: LogPayload = {
    level,
    message,
    data,
    timestamp: new Date().toISOString(),
  };

  switch (level) {
    case "error":
      console.error(`[ePass] ${message}`, data ?? "");
      break;
    case "warn":
      console.warn(`[ePass] ${message}`, data ?? "");
      break;
    case "info":
      console.info(`[ePass] ${message}`, data ?? "");
      break;
  }

  if (import.meta.env.DEV) {
    try {
      const existing = JSON.parse(
        sessionStorage.getItem("epass_logs") || "[]",
      );
      existing.push(payload);
      if (existing.length > 100) existing.shift();
      sessionStorage.setItem("epass_logs", JSON.stringify(existing));
    } catch {
    }
  }
}

export const logger = {
  info: (message: string, data?: unknown) => log("info", message, data),
  warn: (message: string, data?: unknown) => log("warn", message, data),
  error: (message: string, data?: unknown) => log("error", message, data),
};
