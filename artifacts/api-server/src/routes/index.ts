// Route aggregator: combines all sub-routers into a single Express router.
// Mounted at /api in app.ts, so all route paths here are relative to /api.

import { Router, type IRouter } from "express";
import healthRouter from "./health";
import runTaskRouter from "./run-task";

const router: IRouter = Router();

router.use(healthRouter);      // mounts GET /api/healthz
router.use(runTaskRouter);     // mounts POST /api/run-task and GET /api/run-task/stream

export default router;
