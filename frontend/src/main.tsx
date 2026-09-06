import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { initTheme } from "./theme";
import "./i18n";
import "./index.css";
import "./styles/landing.css";
import "./styles/services.css";
// Loaded last: contrast fixes that must win over the rules above.
import "./styles/theme.css";

// Before the first render, so there is no flash of the wrong theme.
initTheme();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
