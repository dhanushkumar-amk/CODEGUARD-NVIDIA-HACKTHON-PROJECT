import React from 'react';
import Header from './components/Header';
import LoginForm from './components/LoginForm';
import CardList from './components/CardList';

export function App() {
  return (
    <div className="app-container">
      <Header />

      {/* Planted Bug 10: Missing <main> landmark - content wrapped in generic <div> (WCAG 1.3.1) */}
      <div className="main-content">
        <h1>CodeGuard Dashboard</h1>

        {/* Planted Bug 9: Skipped heading level - jumping from <h1> directly to <h3> without <h2> (WCAG 1.3.1) */}
        <h3>System Statistics</h3>

        <p>Live automated accessibility telemetry and compliance dashboard.</p>

        <LoginForm />
        <CardList />
      </div>
    </div>
  );
}

export default App;
