// Application entry point: mounts the React app into the #root DOM element.

import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";  // global Tailwind CSS styles

// The non-null assertion (!) is safe because index.html always includes <div id="root">
createRoot(document.getElementById("root")!).render(<App />);
