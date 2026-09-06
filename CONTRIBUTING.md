# Contributing to SocialUp

Thanks for taking the time to contribute.

## Ground rules

- Keep changes focused. One pull request should address one thing.
- Follow the existing code style. The backend is linted with ruff, the frontend compiles with strict TypeScript.
- Do not commit secrets. Environment files are git-ignored on purpose; always document new settings in the `.env.example` files instead.
- If you change how the wallet or order pipeline works, explain the reasoning in the PR description. Money-handling code is reviewed carefully.

## Setting up a development environment

Follow the "Getting started" section in the README. The Docker option gives you the full stack (PostgreSQL, Redis, Celery) and is the easiest way to test Celery-dependent features.

## Running tests

Backend:

```bash
cd backend
pytest
```

Linting:

```bash
ruff check apps config
```

Frontend:

```bash
cd frontend
npm run build   # type-checks and produces a production build
```

## Making changes

1. Fork the repository and create a branch.
2. Make your changes, with tests for any new behavior.
3. Run the relevant test suite.
4. Open a pull request describing what you changed and why.

## Pull request checklist

- Tests pass locally.
- No changes to `.env` files (only `.env.example`).
- No unrelated formatting churn.
- A short description of the change and any behavior it affects.

## Reporting bugs

Open an issue using the bug report template. Security issues should go through the private channel described in SECURITY.md, not a public issue.