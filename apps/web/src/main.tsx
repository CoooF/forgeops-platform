import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { DesignDirections } from "./design-preview/DesignDirections";
import { SelectedPrototype } from "./prototype/SelectedPrototype";

const root = document.getElementById("root");
if (!root) throw new Error("root element is missing");

const content = window.location.pathname.startsWith(
  "/design-preview/prototype",
) ? (
  <SelectedPrototype />
) : window.location.pathname.startsWith("/design-preview/directions") ? (
  <DesignDirections />
) : (
  <App />
);

createRoot(root).render(<StrictMode>{content}</StrictMode>);
