import { Router } from "express";

const router = Router();

const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";

router.post("/run-task", async (req, res) => {
  try {
    const response = await fetch(`${PYTHON_BACKEND_URL}/api/run-task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (err) {
    req.log.error({ err }, "Failed to proxy to Python backend");
    res.status(502).json({ error: "Backend unavailable. Make sure the Python FastAPI server is running." });
  }
});

router.get("/run-task/stream", async (req, res) => {
  const task = req.query.task as string;
  if (!task?.trim()) {
    res.status(400).json({ error: "task query param must not be empty" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("X-Accel-Buffering", "no");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  try {
    const upstreamUrl = `${PYTHON_BACKEND_URL}/api/run-task/stream?task=${encodeURIComponent(task)}`;
    const response = await fetch(upstreamUrl, {
      headers: { Accept: "text/event-stream" },
    });

    if (!response.ok || !response.body) {
      res.write(`event: error\ndata: ${JSON.stringify({ error: "Backend unavailable" })}\n\n`);
      res.end();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    req.on("close", () => {
      reader.cancel();
    });

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      res.write(chunk);
      if ((res as any).flush) (res as any).flush();
    }

    res.end();
  } catch (err) {
    req.log.error({ err }, "SSE proxy error");
    res.write(`event: error\ndata: ${JSON.stringify({ error: "Backend connection failed" })}\n\n`);
    res.end();
  }
});

export default router;
