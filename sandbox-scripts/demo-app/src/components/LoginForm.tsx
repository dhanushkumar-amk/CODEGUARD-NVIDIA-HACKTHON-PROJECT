import React, { useState } from 'react';

export const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [feedback, setFeedback] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <h2>Account Authentication</h2>

      <div className="form-group">
        <label htmlFor="user-email">Email Address</label>
        <input
          id="user-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>

      <div className="form-group">
        {/* Planted Bug 7: <textarea> without label or aria-label (WCAG 3.3.2) */}
        <textarea
          placeholder="Provide user feedback..."
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
      </div>

      {/* Planted Bug 8: Low contrast text (#d1d5db on #ffffff = ~1.5:1 ratio, fails 4.5:1) (WCAG 1.4.3) */}
      <p style={{ color: '#d1d5db', backgroundColor: '#ffffff' }} className="policy-note">
        By signing in, you agree to our policies.
      </p>

      {/* Planted Bug 6: Positive tabIndex value disrupts focus order (WCAG 2.4.3) */}
      <button type="submit" tabIndex={2} className="btn-submit">
        Sign In
      </button>
    </form>
  );
};

export default LoginForm;
