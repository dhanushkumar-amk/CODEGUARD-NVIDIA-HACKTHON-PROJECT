import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Home } from './pages/Home';
import { ScanProgress } from './pages/ScanProgress';
import { Report } from './pages/Report';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen text-ink flex flex-col px-6 md:px-8 max-w-[1120px] mx-auto w-full">
        <Header />
        <main className="flex-1 w-full">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/scan/:scanId" element={<ScanProgress />} />
            <Route path="/report/:scanId" element={<Report />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="py-8 mt-12 border-t border-line text-[11px] text-muted font-mono uppercase tracking-[0.08em] flex flex-col sm:flex-row items-center justify-between gap-4">
          <span>CodeGuard &bull; Autonomous Accessibility Agent</span>
          <span>Powered by NVIDIA Nemotron on Nebius Token Factory</span>
        </footer>
      </div>
    </BrowserRouter>
  );
};

export default App;
