import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { Overview } from "./pages/Overview";
import { Requests } from "./pages/Requests";
import { TokenAnalytics } from "./pages/TokenAnalytics";
import { Compression } from "./pages/Compression";
import { ContextStorage } from "./pages/ContextStorage";
import { Providers } from "./pages/Providers";
import { Playground } from "./pages/Playground";
import { Settings } from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Overview />} />
          <Route path="playground" element={<Playground />} />
          <Route path="requests" element={<Requests />} />
          <Route path="tokens" element={<TokenAnalytics />} />
          <Route path="compression" element={<Compression />} />
          <Route path="contexts" element={<ContextStorage />} />
          <Route path="providers" element={<Providers />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
