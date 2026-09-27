import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Home } from './pages/Home';
import { ScanProgress } from './pages/ScanProgress';
import { Report } from './pages/Report';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0a0c14] text-slate-100 flex flex-col px-4 sm:px-8 max-w-7xl mx-auto">
        <Header />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/scan/:scanId" element={<ScanProgress />} />
            <Route path="/report/:scanId" element={<Report />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer className="py-6 border-t border-slate-900 text-center text-xs text-slate-500 font-mono">
          CodeGuard &bull; Powered by NVIDIA Nemotron on Nebius Token Factory &amp; Nebius AI Cloud Sandboxes
        </footer>
      </div>
    </BrowserRouter>
  );
};

export default App;
