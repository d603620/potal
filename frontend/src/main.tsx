// src/main.tsx

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import App from "./App";
import Dashboard from "./pages/Dashboard";
import Chatpod from "./pages/Chatpod";
import Login from "./pages/Login";
import Profile from "./pages/Profile";

import FileJsonPage from "./pages/Filejson";
import TroubleSearch from "./pages/TroubleSearch";
import TacitApproval from "./pages/TacitApproval";
import KpiAnalyzerPage from "./pages/KpiAnalyzerPage";
import EduDemo from "./pages/EduDemo";
import LicenseCheckerPage from "./pages/LicenseCheckerPage";
import OracleNlqPage from "./pages/OracleNlqPage";

import "./index.css";
import "./App.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* 共通レイアウト（ヘッダー付き） */}
        <Route path="/" element={<App />}>
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="chatpod" element={<Chatpod />} />
          <Route path="profile" element={<Profile />} />
          <Route path="filejson" element={<FileJsonPage />} />
          <Route path="trouble/search" element={<TroubleSearch />} />
          <Route path="trouble/tacit" element={<TacitApproval />} />
          <Route path="kpi/analyzer" element={<KpiAnalyzerPage />} />
          <Route path="edu-demo" element={<EduDemo />} />
          <Route path="license-checker" element={<LicenseCheckerPage />} />
          <Route path="oracle-nlq" element={<OracleNlqPage />} />
        </Route>

        {/* ログインだけは独立 */}
        <Route path="/login" element={<Login />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
