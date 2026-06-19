import { Router, type IRouter } from "express";
import healthRouter from "./health";
import runTaskRouter from "./run-task";

const router: IRouter = Router();

router.use(healthRouter);
router.use(runTaskRouter);

export default router;
