# Sandbox Execution Scripts

This directory contains utility scripts that execute within isolated **Nebius Sandboxes**.

## Purpose
When CodeGuard proposes an accessibility remediation using NVIDIA Nemotron models:
1. An ephemeral Nebius sandbox microVM or container is provisioned.
2. The patched source code is cloned into the sandbox.
3. The scripts in this directory run:
   - Automated axe-core accessibility auditing on rendered components or built static pages.
   - The target repository's regression test suites (`npm test`, `pytest`, etc.).
   - Comparison of violation counts before and after the patch.
4. Output results and execution logs are reported back to the CodeGuard backend.
