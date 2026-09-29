# CodeGuard Demo App (Accessibility Seed Repo)

This sample React application is intentionally seeded with **10 known WCAG 2.2 accessibility defects** to evaluate automated accessibility detection and remediation pipelines.

## Seeded Accessibility Defects Catalogue

| # | Defect Description | File | Offending Code / Pattern | Target WCAG Criterion | Severity |
|---|-------------------|------|--------------------------|-----------------------|----------|
| **1** | Missing `alt` attribute on `<img>` | `src/components/Header.tsx` | `<img src="/company-logo.svg" className="h-8" />` | **1.1.1 Non-text Content** | Critical |
| **2** | Form `<input>` without associated label or `aria-label` | `src/components/Header.tsx` | `<input id="search-box" type="search" placeholder="Search components..." />` | **3.3.2 Labels or Instructions** | Critical |
| **3** | Non-interactive `<div>` with `onClick` without role/tabIndex/keyboard handler | `src/components/Header.tsx` | `<div className="menu-btn" onClick={toggleMenu}>Menu</div>` | **2.1.1 Keyboard** | Serious |
| **4** | Empty icon `<button>` with no text and no `aria-label` | `src/components/Header.tsx` | `<button onClick={handleRefresh}><i className="icon-refresh" /></button>` | **4.1.2 Name, Role, Value** | Serious |
| **5** | Placeholder anchor `<a>` with `href="#"` | `src/components/Header.tsx` | `<a href="#" onClick={handleDocsClick}>Docs & Help</a>` | **2.4.4 Link Purpose (In Context)** | Moderate |
| **6** | Positive `tabIndex` value disrupting focus order | `src/components/LoginForm.tsx` | `<button type="submit" tabIndex={2}>Sign In</button>` | **2.4.3 Focus Order** | Moderate |
| **7** | Form `<textarea>` without label or `aria-label` | `src/components/LoginForm.tsx` | `<textarea placeholder="Provide user feedback..." />` | **3.3.2 Labels or Instructions** | Critical |
| **8** | Hardcoded low-contrast text on white background (below 4.5:1 ratio) | `src/components/LoginForm.tsx` | `<p style={{ color: "#d1d5db", backgroundColor: "#ffffff" }}>By signing in, you agree to our policies.</p>` | **1.4.3 Contrast (Minimum)** | Serious |
| **9** | Skipped heading hierarchy level (`<h1>` to `<h3>` without `<h2>`) | `src/App.tsx` | `<h1>CodeGuard Dashboard</h1>` followed directly by `<h3>System Statistics</h3>` | **1.3.1 Info and Relationships** | Moderate |
| **10** | Missing semantic `<main>` landmark | `src/App.tsx` | Root content rendered in `<div className="main-content">` instead of `<main>` | **1.3.1 Info and Relationships** | Moderate |
