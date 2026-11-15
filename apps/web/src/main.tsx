import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { HealthProvider } from "./lib/health";
import { ToastProvider } from "./lib/toast";
import { router } from "./router";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ToastProvider>
      <AuthProvider>
        <HealthProvider>
          <RouterProvider router={router} />
        </HealthProvider>
      </AuthProvider>
    </ToastProvider>
  </StrictMode>,
);
