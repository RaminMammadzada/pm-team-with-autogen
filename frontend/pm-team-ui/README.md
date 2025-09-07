# PM Team Frontend

Angular 20 standalone dashboard for the PM Team multi-project planning system. It consumes the Python FastAPI backend (exposed by `pm_team.api`) to list projects, inspect recent runs, and view generated sprint plan tasks including WSJF scoring and risk exposure.

## Features

- Project list fetched from `GET /projects`
- Per-project run list via `GET /projects/:slug/runs`
- Plan artifact retrieval (`plan.json`) for a selected run
- Displays task metadata (type, priority, WSJF, risk exposure, status)
- Basic responsive layout (sidebar projects, run pills, tasks table)
- Simple refresh button (re-fetch projects)

## Getting Started

Prerequisites:
- Node.js 18+ (LTS recommended)
- Backend running locally on `http://localhost:8000` (start with `uvicorn pm_team.api:app --reload` from repo root)

Install deps:
```bash
npm install
```

Run dev server:
```bash
npx ng serve
```
Visit http://localhost:4200

If your backend runs on a different host/port, you can inject a global before bundle load (temporary approach) in `index.html`:
```html
<script>window.__PM_TEAM_API__ = 'http://127.0.0.1:8001';</script>
```

Better environment handling (Angular `environment.ts`) can be added later.

## Backend API Contract (Consumed Endpoints)

| Endpoint | Purpose | Expected Shape (abridged) |
|----------|---------|---------------------------|
| `GET /projects` | List projects | `[ { slug, name, created_at? } ]` |
| `GET /projects/:slug/runs` | List runs (latest first) | `[ { run_id, created_at? } ]` |
| `GET /projects/:slug/runs/:run_id/artifact/plan.json` | Sprint plan artifact | `{ tasks: [ { id, title, type, priority, wsjf_score, risk_exposure, status } ] }` |

Errors are logged to `console.error` only (no in-app toasts yet).

## Scripts

```bash
npm run start     # same as ng serve
npm run build     # production build to dist/
npm test          # unit tests (Karma + Jasmine)
```

## Testing

Current tests cover component creation & header render. Add more tests by placing `*.spec.ts` under `src/`.

## Roadmap Ideas (Frontend)

- Dedicated data service with retry/backoff
- Environment-based API configuration
- Plan diffing across runs
- Task filtering & sorting (WSJF desc, risk desc, type)
- Loading/error toast notifications
- Dark mode toggle
- E2E tests (Playwright or Cypress)

## Development Notes

This app uses Angular standalone components (no NgModule). Root component (`app.ts`) directly imports `HttpClientModule`. Styling is minimal and scoped in `app.scss`.

---
Generated originally by Angular CLI 20.2.2 and then customized for PM Team.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
