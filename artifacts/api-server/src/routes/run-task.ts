// Task proxy routes: forwards requests to the Python FastAPI backend.
// POST /api/run-task: synchronous proxy; GET /api/run-task/stream: SSE proxy.
// If the Python backend is unavailable, returns a 502 with a descriptive error.

import { Router } from "express";

const router = Router();

// Read the Python backend URL from the environment; default to localhost for local dev
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";

router.post("/run-task", async (req, res) => {
  try {
    // Forward the request body to the Python FastAPI /api/run-task endpoint
    const response = await fetch(`${PYTHON_BACKEND_URL}/api/run-task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),  // pass through whatever the client sent
    });
    const data = await response.json();
    res.status(response.status).json(data);  // mirror the backend's status code
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

  // Set SSE headers so the client receives a streaming response
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");      // prevent proxies from buffering
  res.setHeader("X-Accel-Buffering", "no");         // disable nginx buffering
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();  // send headers immediately so the client can start reading

  try {
    const upstreamUrl = `${PYTHON_BACKEND_URL}/api/run-task/stream?task=${encodeURIComponent(task)}`;
    const response = await fetch(upstreamUrl, {
      headers: { Accept: "text/event-stream" },  // request SSE from the Python backend
    });

    if (!response.ok || !response.body) {
      // Backend returned an error — send a terminal error event and close
      res.write(`event: error\ndata: ${JSON.stringify({ error: "Backend unavailable" })}\n\n`);
      res.end();
      return;
    }

    const reader = response.body.getReader();  // read the upstream SSE byte-by-byte
    const decoder = new TextDecoder();

    // Cancel the upstream stream if the client disconnects early
    req.on("close", () => {
      reader.cancel();
    });

    // Pipe bytes from the upstream SSE stream to the client
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;  // upstream stream finished
      const chunk = decoder.decode(value, { stream: true });  // decode bytes keeping stream state
      res.write(chunk);
      if ((res as any).flush) (res as any).flush();  // flush to client immediately (compression middleware compat)
    }

    res.end();
  } catch (err) {
    req.log.error({ err }, "SSE proxy error");
    res.write(`event: error\ndata: ${JSON.stringify({ error: "Backend connection failed" })}\n\n`);
    res.end();
  }
});

export default router;
