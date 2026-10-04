import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { ScrollToTop } from './components/ScrollToTop';
import { Home } from './pages/Home';
import { ScanProgress } from './pages/ScanProgress';
import { Report } from './pages/Report';
import { Privacy } from './pages/Privacy';
import { Terms } from './pages/Terms';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <div className="min-h-screen text-ink flex flex-col px-6 md:px-8 max-w-[1120px] mx-auto w-full">
        <Header />
        <main className="flex-1 w-full">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/scan/:scanId" element={<ScanProgress />} />
            <Route path="/report/:scanId" element={<Report />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
};

export default App;
