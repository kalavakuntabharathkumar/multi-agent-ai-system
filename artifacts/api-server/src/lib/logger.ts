// Shared pino logger instance for the Express API server.
// Uses pino-pretty for human-readable output in development; plain JSON in production.

import pino from "pino";

const isProduction = process.env.NODE_ENV === "production";

export const logger = pino({
  level: process.env.LOG_LEVEL ?? "info",  // allow overriding log level via env var
  redact: [
    // Automatically strip sensitive headers from all log output
    "req.headers.authorization",
    "req.headers.cookie",
    "res.headers['set-cookie']",
  ],
  // In development, use pino-pretty for colorized, human-readable logs
  ...(isProduction
    ? {}
    : {
        transport: {
          target: "pino-pretty",
          options: { colorize: true },
        },
      }),
});
