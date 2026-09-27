import React from 'react';
import { Header } from './components/Header';
import { HomePage } from './pages/HomePage';

export const App: React.FC = () => {
  return (
    <div className="app-container">
      <Header />
      <main>
        <HomePage />
      </main>
      <footer className="footer">
        CodeGuard &copy; 2026 &bull; Built with Nebius Token Factory & NVIDIA Nemotron Models
      </footer>
    </div>
  );
};

export default App;
