import React, { useState } from 'react';

export const Header: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  const handleDocsClick = (e: React.MouseEvent) => {
    e.preventDefault();
  };

  return (
    <header className="site-header">
      {/* Planted Bug 1: <img> without alt attribute (WCAG 1.1.1) */}
      <img src="/company-logo.svg" className="h-8" />

      {/* Planted Bug 2: <input> without label, aria-label, or aria-labelledby (WCAG 3.3.2) */}
      <input id="search-box" type="search" placeholder="Search components..." />

      {/* Planted Bug 3: <div> with onClick but no role, tabIndex, or keyboard handler (WCAG 2.1.1) */}
      <div className="menu-btn" onClick={toggleMenu}>
        Menu
      </div>

      {/* Planted Bug 4: <button> with no text content and no aria-label (WCAG 4.1.2) */}
      <button onClick={handleRefresh}>
        <i className="icon-refresh" />
      </button>

      {/* Planted Bug 5: <a> with placeholder '#' href (WCAG 2.4.4) */}
      <a href="#" onClick={handleDocsClick}>
        Docs & Help
      </a>
    </header>
  );
};

export default Header;
