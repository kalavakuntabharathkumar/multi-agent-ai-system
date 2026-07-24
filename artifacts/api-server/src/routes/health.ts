// Health check route: GET /api/healthz returns {"status":"ok"} if the server is running.
// The response is validated against the HealthCheckResponse Zod schema before sending.

import { Router, type IRouter } from "express";
import { HealthCheckResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/healthz", (_req, res) => {
  const data = HealthCheckResponse.parse({ status: "ok" });  // validate shape before responding
  res.json(data);
});

export default router;
