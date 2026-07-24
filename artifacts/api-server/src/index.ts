// Server entry point: reads the PORT environment variable and starts listening.
// Exits with an error if PORT is missing or invalid.

import app from "./app";
import { logger } from "./lib/logger";

const rawPort = process.env["PORT"];

// Fail fast if PORT is not provided — the server cannot bind without it
if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

// Guard against non-numeric or zero/negative port values
if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

// Start listening; log a fatal error and exit if binding fails
app.listen(port, (err) => {
  if (err) {
    logger.error({ err }, "Error listening on port");
    process.exit(1);
  }

  logger.info({ port }, "Server listening");
});
