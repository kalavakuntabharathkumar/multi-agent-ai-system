// Express application setup: attaches middleware (logging, CORS, body parsing)
// and mounts all API routes under the /api prefix.

import express, { type Express } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

// Attach structured HTTP request/response logging via pino-http
app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        // Log only the essential request fields to avoid noisy logs
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],  // strip query string from logged URL
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,  // log only the status code for responses
        };
      },
    },
  }),
);
app.use(cors());                              // allow cross-origin requests from any origin
app.use(express.json());                      // parse JSON request bodies
app.use(express.urlencoded({ extended: true })); // parse URL-encoded form bodies

app.use("/api", router);  // mount all route handlers under the /api path prefix

export default app;
