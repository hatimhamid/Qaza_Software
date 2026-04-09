# Umoor Qaza Saifee Nagar Documentation

## 1. Overview

Umoor Qaza Saifee Nagar is a lightweight web-based case management system for a community mediation center. It is designed to run as a simple server, store case data directly in a SQLite database, and provide authenticated access for three user roles:

- `Admin`
- `Editor`
- `Viewer`

The application supports:

- secure username/password login
- case creation and editing
- comments and notes on each case
- subtasks linked to a case
- dashboard metrics
- analytics filters and charts
- CSV export
- responsive desktop and mobile layouts

The system is intentionally dependency-light. It uses Python’s built-in HTTP server stack plus SQLite, which makes it easy to run on a local machine or internal server without a large deployment footprint.

## 2. Project Structure

```text
New project/
|-- app.py
|-- README.md
|-- DOCUMENTATION.md
|-- .gitignore
|-- data/
|   `-- umoor_qaza.db
`-- static/
    |-- index.html
    |-- dashboard.html
    |-- cases.html
    |-- analytics.html
    |-- settings.html
    |-- app.js
    `-- styles.css
```

### Main files

- `app.py`
  Handles HTTP serving, authentication, session management, API routing, database setup, CRUD operations, analytics aggregation, and CSV export.

- `static/index.html`
  Login page.

- `static/dashboard.html`
  Overview page with headline metrics and summary charts.

- `static/cases.html`
  Main case management workspace with filter panel, case list, case form, comments, and subtasks.

- `static/analytics.html`
  Reporting page with filter-driven visual charts and CSV export.

- `static/settings.html`
  System summary page showing permission model and user directory.

- `static/app.js`
  Client-side logic for page bootstrapping, API calls, rendering, filtering, permissions, and interactions.

- `static/styles.css`
  Shared responsive UI styling across all pages.

## 3. Technology Stack

- Backend: Python 3
- HTTP server: `http.server` with `ThreadingHTTPServer`
- Database: SQLite
- Frontend: HTML, CSS, vanilla JavaScript
- Authentication: session cookie stored in memory on the server

## 4. Core Functional Areas

### 4.1 Authentication

Users log in with a username and password. The server validates credentials against the `users` table and creates an in-memory session token stored in a cookie.

Current seeded users:

- `admin / admin123`
- `editor / editor123`
- `viewer / viewer123`

### 4.2 Roles and Permissions

#### Admin

- can access settings
- can create cases
- can edit cases
- can add comments
- can create and update subtasks

#### Editor

- can create cases
- can edit cases
- can add comments
- can create and update subtasks

#### Viewer

- read-only access
- can open dashboard, analytics, settings, and cases pages
- cannot modify records

### 4.3 Case Management

Each case contains the following fields:

- `Case ID`
- `Applicant`
- `Complainant`
- `Respondent`
- `Summary`
- `Case Type`
- `Status`
- `Created Date`
- `Start Date`
- `Documents Link`
- `Due Date`
- `Completed Date`
- `Assignee`
- `Priority`

Supported case types:

- `Marital`
- `Inheritance`
- `Business`

Supported statuses:

- `In-progress`
- `Impasse`
- `New`
- `Resolved`
- `Dropped`
- `Hold`

Supported priorities:

- `Low`
- `Medium`
- `High`
- `Critical`

### 4.4 Comments and Notes

Each case can have multiple comments. Comments are stored with:

- case reference
- comment body
- author user ID
- creation timestamp

### 4.5 Subtasks

Each case can have multiple subtasks. Each subtask includes:

- title
- completion flag
- due date
- assignee
- created timestamp
- updated timestamp

### 4.6 Dashboard and Analytics

The system can slice and summarize case data by:

- assignee
- due date
- case type
- status
- start date
- completion date
- priority

The analytics views currently include:

- status mix
- cases by type
- assignee load
- priority spread
- case starts by month

### 4.7 CSV Export

CSV export includes all major case fields except:

- summary/description
- comments
- subtasks

This aligns with the requirement to exclude narrative and activity data from the export.

## 5. Database Design

The SQLite database is automatically created at:

```text
data/umoor_qaza.db
```

### 5.1 Tables

#### `users`

Stores application users.

Key fields:

- `id`
- `username`
- `full_name`
- `password_hash`
- `role`
- `created_at`

#### `cases`

Stores mediation cases.

Key fields:

- `id`
- `case_id`
- `applicant`
- `complainant`
- `respondent`
- `summary`
- `case_type`
- `status`
- `created_date`
- `start_date`
- `documents_link`
- `due_date`
- `completed_date`
- `assignee`
- `priority`
- `created_at`
- `updated_at`

#### `comments`

Stores notes/comments attached to a case.

Key fields:

- `id`
- `case_id`
- `body`
- `author_id`
- `created_at`

#### `subtasks`

Stores task items attached to a case.

Key fields:

- `id`
- `case_id`
- `title`
- `is_done`
- `due_date`
- `assignee`
- `created_at`
- `updated_at`

### 5.2 Relationships

- one `case` can have many `comments`
- one `case` can have many `subtasks`
- one `user` can author many `comments`

Foreign key constraints are enabled in SQLite.

## 6. Application Flow

### 6.1 Startup

When `app.py` starts:

1. it creates the `data` directory if needed
2. it initializes the SQLite database
3. it creates required tables if they do not exist
4. it seeds default users
5. it seeds sample cases if the database is empty
6. it starts an HTTP server on port `8000`

### 6.2 Login Flow

1. user opens `/`
2. login page submits credentials to `/api/login`
3. server validates credentials
4. server creates a session cookie
5. user navigates to the application pages

### 6.3 Case Workflow

1. open the Cases page
2. filter the case list as needed
3. select an existing case or create a new one
4. update case fields
5. add comments and subtasks
6. save changes

## 7. Frontend Page Breakdown

### 7.1 Login Page

Path:

```text
/
```

Purpose:

- collect credentials
- show seeded demo accounts
- optionally show an existing active session

### 7.2 Dashboard Page

Path:

```text
/dashboard.html
```

Purpose:

- present top-level case metrics
- show summary charts
- display recent cases

### 7.3 Cases Page

Path:

```text
/cases.html
```

Purpose:

- browse the case register
- apply filters
- edit case details
- manage comments and subtasks

### 7.4 Analytics Page

Path:

```text
/analytics.html
```

Purpose:

- view chart-driven analysis
- filter the dataset
- export filtered case data to CSV

### 7.5 Settings Page

Path:

```text
/settings.html
```

Purpose:

- explain role model
- show user directory
- provide a simple system summary

## 8. API Reference

All API routes are handled by `app.py`.

### 8.1 Session and Authentication

#### `GET /api/session`

Returns the currently logged-in user if a valid session exists.

Response:

```json
{
  "user": {
    "id": 1,
    "username": "admin",
    "full_name": "System Administrator",
    "role": "Admin"
  }
}
```

#### `POST /api/login`

Authenticates a user.

Request:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

#### `POST /api/logout`

Clears the active session.

### 8.2 Metadata

#### `GET /api/meta`

Returns:

- case types
- statuses
- priorities
- roles
- users list

### 8.3 Cases

#### `GET /api/cases`

Returns the filtered case list.

Supported query parameters:

- `search`
- `assignee`
- `case_type`
- `status`
- `priority`
- `created_date_from`
- `created_date_to`
- `start_date_from`
- `start_date_to`
- `due_date_from`
- `due_date_to`
- `completed_date_from`
- `completed_date_to`

#### `GET /api/cases/{id}`

Returns:

- case details
- comments
- subtasks

#### `POST /api/cases`

Creates a case. Requires `Admin` or `Editor`.

#### `PUT /api/cases/{id}`

Updates a case. Requires `Admin` or `Editor`.

### 8.4 Comments

#### `POST /api/cases/{id}/comments`

Adds a comment to a case. Requires `Admin` or `Editor`.

### 8.5 Subtasks

#### `POST /api/cases/{id}/subtasks`

Creates a subtask. Requires `Admin` or `Editor`.

#### `PUT /api/cases/{id}/subtasks/{subtaskId}`

Updates a subtask. Requires `Admin` or `Editor`.

### 8.6 Analytics and Export

#### `GET /api/dashboard`

Returns summary and chart datasets.

#### `GET /api/export.csv`

Exports matching case records to CSV.

## 9. Running the Application

### 9.1 Requirements

- Python 3.x installed

### 9.2 Start the Server

From the project root:

```powershell
python app.py
```

Expected output:

```text
Umoor Qaza Saifee Nagar server running at http://127.0.0.1:8000
```

Then open:

```text
http://127.0.0.1:8000
```

### 9.3 Stop the Server

Press `Ctrl+C` in the terminal running the server.

## 10. Initial Data

On first startup, the app seeds:

- 3 default users
- sample mediation cases

This helps verify that the UI, filters, charts, and CSV export all work immediately.

## 11. Security Notes

Current security model is suitable for a simple internal deployment or prototype. Before production use, consider strengthening:

- HTTPS termination
- stronger password policy
- password reset and account management
- persistent session storage
- CSRF protection
- audit logging
- account lockout and rate limiting
- secure secret/config management

## 12. Operational Notes

### Database behavior

- all data is stored in a local SQLite file
- sessions are stored in server memory
- restarting the server clears active sessions
- data remains intact because it is stored in SQLite

### File serving

- HTML, CSS, and JS files are served from the `static` directory
- API responses are served under `/api/*`

## 13. Known Limitations

- sessions are not persistent across server restarts
- settings page is informational and does not yet include settings edit forms
- user management UI is not yet implemented
- authentication uses seeded/local accounts only
- no delete endpoints currently exist for cases, comments, or subtasks
- CSV export excludes summary, comments, and subtasks by design

## 14. Recommended Future Enhancements

- add create/edit user management for admins
- add delete/archive functionality for cases and subtasks
- add attachment upload support instead of link-only document references
- add password change flow
- add audit trail/history per case
- add pagination for large datasets
- add search highlighting and saved filters
- add backup and restore utilities
- add deployment configuration for LAN or cloud hosting

## 15. Troubleshooting

### Problem: Login page does not appear

Possible causes:

- an old browser session is still active
- browser cache is using old JavaScript/CSS

Actions:

- hard refresh the browser with `Ctrl+F5`
- use the Sign Out action on the login page if a session is detected

### Problem: Changes are not saving

Possible causes:

- logged in as `Viewer`
- required case fields are missing

Actions:

- log in as `Admin` or `Editor`
- confirm required fields are filled in

### Problem: CSV export is empty

Possible causes:

- current filters return no matching cases

Actions:

- clear filters and retry export

### Problem: Server will not start

Possible causes:

- Python is not installed
- port `8000` is already in use

Actions:

- verify with `python --version`
- stop the process using port `8000` or change the port in `app.py`

## 16. Quick Reference

### Default login accounts

- `admin / admin123`
- `editor / editor123`
- `viewer / viewer123`

### Important paths

- app entry point: `app.py`
- database file: `data/umoor_qaza.db`
- frontend files: `static/`

### Main URLs

- login: `/`
- dashboard: `/dashboard.html`
- cases: `/cases.html`
- analytics: `/analytics.html`
- settings: `/settings.html`

## 17. Summary

This application provides a focused and practical mediation case-management system with direct database sync, structured roles, responsive UI, and operational reporting. It is simple to run, easy to inspect, and straightforward to extend.
