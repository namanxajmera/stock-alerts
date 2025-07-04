# Contributing Guidelines

Thank you for your interest in contributing to the StockViz project! To ensure a smooth and collaborative development process, please follow these guidelines.

## Development Workflow

1.  **Create an Issue:** Before starting work on a new feature or bug fix, please create an issue in the repository to discuss the proposed changes.
2.  **Fork and Branch:** Fork the repository and create a new feature branch from `main` for your changes.
    ```sh
    git checkout -b feature/my-new-feature
    ```
3.  **Local Development:** Set up your local environment by following the [SETUP.md](./SETUP.md) guide.
4.  **Make Changes:** Write your code, ensuring it adheres to the standards below.
5.  **Update Documentation:** If your changes affect the architecture, dependencies, API, or environment variables, you **must** update the relevant documentation (`ARCHITECTURE.md`, `API.md`, `SETUP.md`, etc.) in the same pull request. All technical claims must be backed by code references.
6.  **Submit a Pull Request:** Push your branch to your fork and open a pull request against the main repository's `main` branch. Provide a clear description of the changes.

## Coding Standards

*   **Python:** Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines. Use a linter like `flake8` or `black` to maintain consistent formatting.
*   **Logging:** Use the central logger for important events. Do not use `print()` statements for logging in the application code. The logger is configured in [`app.py:setup_logging()`](./app.py).
*   **Error Handling:** Use `try...except` blocks to gracefully handle potential errors, especially around API calls and database interactions. Log exceptions with `logger.error(..., exc_info=True)`.
*   **Security:**
    *   Never commit sensitive information (tokens, passwords) to the repository. Use environment variables as defined in [`.env.example`](./.env.example).
    *   Sanitize and validate all user input, such as the ticker symbol validation in [`app.py:validate_ticker_symbol()`](./app.py).

## Database Migrations

If your changes require a modification to the database schema, you must create a new SQL migration file.

1.  **Create a new file** in the [`migrations/`](./migrations/) directory.
2.  **Name the file** using a sequential number and a descriptive name (e.g., `002_add_user_preferences.sql`).
3.  **Write the SQL `ALTER TABLE` or `CREATE TABLE` statements** in the file. Make sure your changes are idempotent or safe to run multiple times if possible.

The application's migration runner in [`db_manager.py`](./db_manager.py) will automatically apply new migrations in order.

## Documentation

**Documentation is not optional.** Every pull request that introduces a change in functionality must include corresponding updates to the documentation. The core principle is that the documentation must be an accurate, verifiable reflection of the codebase. Every technical statement must be supported by a link to the specific file or function that implements it.
