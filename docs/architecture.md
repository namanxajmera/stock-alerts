# System Architecture

This document provides a comprehensive overview of the Stock Alerts application's architecture, designed for both product managers and engineers. The system combines interactive web analytics with automated Telegram alerts through a unified backend.

## 1. High-Level Overview

Stock Alerts is a monolithic Flask application organized into a clean, service-oriented structure following a 3-tier architecture with proper dependency injection.

### 1.1 Architecture Tiers

1.  **Presentation Tier:** Interactive web dashboard built with ApexCharts.js and vanilla JavaScript.
2.  **Application Tier:** Flask backend with modular services, dependency injection, and background job processing.
3.  **Data Tier:** PostgreSQL database with a repository pattern and automated migrations.

### 1.2 Business Value Architecture

**For Product Managers:** This unified architecture powers two distinct user experiences:
- **Rich Web Interface:** Interactive charts and analytics for detailed stock analysis.
- **Telegram Bot:** Simple, conversational interface for managing watchlists and receiving alerts.

The single backend ensures data consistency and reduces operational complexity while enabling automated, proactive alerts without external dependencies.

**For Engineers:** Clean separation of concerns with:
- **Dependency Injection:** Services are constructed with their dependencies in `app.py`, making the system modular and easy to test.
- Service-oriented business logic.
- Automated database migrations.
- Built-in caching and connection pooling.
- Comprehensive input validation and security.
- Ready-to-deploy configuration.

## 2. Component Architecture

### 2.1 Frontend Layer

The frontend is a single-page application focused on interactive stock data visualization.

**Technology Stack:**
- HTML5 with semantic structure
- CSS3 with custom properties and responsive design
- Vanilla JavaScript with modular ES6 patterns
- [ApexCharts.js](https://apexcharts.com/) for advanced charting

**Core Files:**
- [`templates/index.html`](../templates/index.html) - Main HTML structure with ApexCharts CDN integration
- [`static/css/style.css`](../static/css/style.css) - Complete styling with CSS variables and responsive layout
- [`static/js/main.js`](../static/js/main.js) - StockAnalyzer module with chart rendering and API integration

### 2.2 Backend Application Layer

The Flask backend is orchestrated through a modular architecture with clear separation of concerns, managed by a central dependency injection container in `app.py`.

#### 2.2.1 Application Bootstrap
**Entry Point:** [`app.py`](../app.py)
- Initializes the Flask application.
- Loads configuration from environment variables.
- **Dependency Injection:** Instantiates and wires all services (`StockService`, `AdminService`, `NotificationService`), features (`PeriodicChecker`, `WebhookHandler`), and the `DatabaseManager`.
- Stores all major components in the Flask `app` context, making them accessible to routes and scheduled jobs.
- Registers all blueprint routes.
- Configures and starts the background scheduler, passing it the `app` context to ensure jobs have access to services.

#### 2.2.2 Route Layer (`routes/`)
Blueprint-based route organization. Routes are responsible for handling HTTP requests and delegating business logic to the service layer.

- **[`routes/api_routes.py`](../routes/api_routes.py)** - Public stock data endpoints.
- **[`routes/webhook_routes.py`](../routes/webhook_routes.py)** - Telegram bot integration.
- **[`routes/admin_routes.py`](../routes/admin_routes.py)** - Administrative interface.
- **[`routes/health_routes.py`](../routes/health_routes.py)** - System monitoring.

#### 2.2.3 Service Layer (`services/`)
Encapsulates core business logic. Services are injected with their dependencies (like `DatabaseManager` or other services) via their constructors.

- **[`services/stock_service.py`](../services/stock_service.py)** - Handles all logic related to stock data processing, analysis, and caching.
- **[`services/admin_service.py`](../services/admin_service.py)** - Manages admin operations. It now receives the `PeriodicChecker` as a dependency to trigger manual checks.
- **[`services/auth_service.py`](../services/auth_service.py)** - Handles authentication and authorization for protected endpoints.
- **[`services/notification_service.py`](../services/notification_service.py)** - **New!** This service acts as a crucial abstraction layer for sending notifications. It decouples the `PeriodicChecker` and other services from the specific implementation of how notifications are sent (e.g., via the `WebhookHandler`).

#### 2.2.4 Core Features (`features/`)
Contains the core, framework-agnostic features of the application.

- **[`features/webhook_handler.py`](../features/webhook_handler.py)** - Processes incoming Telegram messages, validates them, and interacts with the `DatabaseManager` to manage user data and watchlists.
- **[`features/periodic_checker.py`](../features/periodic_checker.py)** - Handles the logic for checking watchlists and identifying when alerts should be triggered. It receives the `DatabaseManager` and `NotificationService` as dependencies.

#### 2.2.5 Utility Layer (`utils/`)
- **[`utils/scheduler.py`](../utils/scheduler.py)** - The background job scheduler (APScheduler) is now correctly integrated with the Flask application context. The `setup_scheduler` function takes the `app` object to create jobs that can access application services, fixing a critical bug from the previous architecture.

### 2.3 Data Layer

PostgreSQL database with a repository pattern for data access and automated schema management.

#### 2.3.1 Database Management
**[`database/database_manager.py`](../database/database_manager.py)** - A central class that manages the connection pool and provides access to various data repositories.

**Repositories (`database/repositories/`)** - Each repository is responsible for data access logic for a specific domain (e.g., `user_repository.py`, `stock_repository.py`). This cleans up the `DatabaseManager` and organizes queries effectively.

#### 2.3.2 Schema Management
**Migration System:** [`migrations/`](../migrations/) directory contains versioned SQL files for automated, idempotent schema updates.

## 3. Data Flow Architecture

### 3.1 Automated Alert Generation Flow (Corrected)

The data flow for automated alerts is now more robust and reliable.

1.  **Scheduler Trigger:** The `APScheduler` in `utils/scheduler.py`, running within the Flask app context, executes its scheduled job.
2.  **Job Execution:** The job wrapper function accesses the `periodic_checker` instance from the `current_app` context.
3.  **Watchlist Check:** `PeriodicChecker.check_watchlists()` is called.
4.  **Data Retrieval:** The checker fetches all active watchlists from the database via its injected `DatabaseManager`.
5.  **Data Processing Loop:** For each unique stock, it fetches data (from cache or the Tiingo API) and calculates metrics.
6.  **Alert Logic:** It checks if the current price deviation meets the alert criteria.
7.  **Notification Dispatch:** If an alert is triggered, the `PeriodicChecker` **does not** call the `WebhookHandler` directly. Instead, it calls `self.notification_service.send_batched_alerts()`.
8.  **Decoupled Sending:** The `NotificationService` receives the alert data and is responsible for formatting it and sending it to the appropriate channel. Currently, it calls the `WebhookHandler` to send a Telegram message.
9.  **Logging:** The `NotificationService` or `WebhookHandler` logs the alert in the database.

This new flow correctly decouples the core business logic (`PeriodicChecker`) from the notification delivery mechanism (`WebhookHandler`), making the system more modular and easier to extend with new notification channels in the future.

## 4. Security Architecture

Security remains a top priority, with no major changes to the established patterns.

- **Authentication & Authorization:** HTTP Basic Auth and API keys for admin access; HMAC validation for Telegram webhooks.
- **Input Validation & Sanitization:** Strict validation of all user inputs (tickers, periods, commands).
- **SQL Injection Prevention:** Exclusive use of parameterized queries through the repository pattern.
- **Secrets Management:** All sensitive keys and tokens are managed via environment variables.

## 5. Deployment & Operations

Deployment and operational strategies remain the same, with a focus on automated, reliable deployments via PaaS providers or container orchestration.
