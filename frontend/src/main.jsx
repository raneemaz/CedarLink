import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { CurrencyProvider } from "./context/CurrencyContext";
import { ThemeProvider } from "./context/ThemeContext";
import { NotificationsProvider } from "./context/NotificationsContext";
import AppToaster from "./components/common/AppToaster";
import "react-toastify/dist/ReactToastify.css";
import "./i18n/i18n";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <CurrencyProvider>
          <NotificationsProvider>
            <BrowserRouter>
              <App />
              <AppToaster />
            </BrowserRouter>
          </NotificationsProvider>
        </CurrencyProvider>
      </ThemeProvider>
    </AuthProvider>
  </React.StrictMode>
);