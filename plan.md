# Modal Sandbox demo for CodeGuard

## Goal

Run one accessibility patch against CodeGuard’s checked-in React app in a CPU-only Modal Sandbox. The demo should show the same browser check failing before the patch and passing afterward, alongside the fixture’s test results. Keep the existing model configuration and scan API in place.

## First demo

1. Add an opt-in Python runner under `backend/scripts/`. Use a dedicated Modal app and authenticate the runner with the standard Modal credentials on the host. Verify the installed Modal SDK’s file-transfer, execution, timeout, and termination APIs against its reference.
2. Build a pinned image with Node.js, npm, Git, Playwright Chromium, and the matching system libraries. Copy only `sandbox-scripts/demo-app/` and the trusted `backend/app/resources/run-axe-check.js`. Load the latter as `.cjs` because the fixture uses ES modules. The fixture currently has no npm lockfile. Add one in the implementation PR and use `npm ci` for repeatable runs.
3. Start the fixture’s Vite app on loopback and run the existing axe runner against it. Confirm that axe reports `button-name` for the unlabeled refresh button in `src/components/Header.tsx`. If the baseline lacks that specific finding, stop and report the baseline failure.
4. Apply a checked-in unified diff that adds `aria-label="Refresh page"` to the refresh button. Restart the app, audit the same route, and confirm axe no longer reports `button-name` for that button. Use a Playwright assertion to check that a button named “Refresh page” is visible. Run `npm test` and require actual tests to execute successfully. The existing fixture tests check source structure, so the browser assertion supplies behavioral evidence.
5. Print the sandbox ID, before and after rule results, test summary, command exit codes, and elapsed times. Treat invalid axe output, unavailable Chromium, timeouts, and test failures as failed verification. Terminate in a `finally` block and configure a sandbox lifetime limit so interrupted runs expire.

## Integrate after the demo passes

- Add an opt-in Modal provider behind the existing `sandbox_client.py` interface. Preserve the contracts for `create_sandbox`, `run_command`, `upload_files`, and `destroy_sandbox` so the orchestrator and the axe and test runners can reuse their normal flow.
- Give each patch a fresh sandbox. Consider filesystem snapshots once the full flow is repeatable and state isolation has been verified.
- Keep Modal, GitHub, and model credentials in the trusted backend. Keep application ports internal. Verify that dependency installation can use approved registries and that untrusted app and test processes run with outbound access disabled. Require these controls before enabling arbitrary repositories. Fail closed if Modal cannot start or enforce the configured isolation.
- Test provider contract handling with a mocked SDK. Run an authenticated smoke test against the fixture and force a failing command to confirm the demo reports failure and still cleans up.

## Implementation PR acceptance

- A single documented command runs the Modal demo with an authenticated account.
- The browser records the target violation before the patch and its absence afterward. The named-button assertion and fixture tests pass.
- A failing run exits nonzero and the sandbox is terminated.
- The PR includes a sanitized output sample showing both audit results and the test summary.

[Modal Sandbox guide](https://modal.com/docs/guide/sandboxes) · [Modal Sandbox SDK reference](https://modal.com/docs/reference/modal.Sandbox)
