"""!
@file app.py
@brief Backend server for the Umoor Qaza Saifee Nagar case management application.

This module provides:
- SQLite database initialization and seeding
- session-based authentication
- case, comment, and subtask APIs
- dashboard aggregation and CSV export
- static file serving for the frontend pages
"""

import csv
import hashlib
import hmac
import io
import json
import secrets
import sqlite3
import threading
from datetime import UTC, datetime
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "umoor_qaza.db"
SESSION_COOKIE = "umoor_qaza_session"

CASE_TYPES = ["Marital", "Inheritance", "Business"]
CASE_STATUSES = ["In-progress", "Impasse", "New", "Resolved", "Dropped", "Hold"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
ROLES = ["Admin", "Editor", "Viewer"]
DATE_FIELDS = ["created_date", "start_date", "due_date", "completed_date"]
EXPORT_FIELDS = [
    "case_id",
    "applicant",
    "complainant",
    "respondent",
    "case_type",
    "status",
    "created_date",
    "start_date",
    "documents_link",
    "due_date",
    "completed_date",
    "assignee",
    "priority",
]

SESSIONS = {}
SESSION_LOCK = threading.Lock()


def utc_now():
    """!
    @brief Return the current UTC timestamp as an ISO-8601 string.

    @return Current UTC timestamp without microseconds.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def json_response(handler, status, payload):
    """!
    @brief Send a JSON HTTP response.

    @param handler Active HTTP request handler.
    @param status HTTP status code.
    @param payload Python object that can be serialized to JSON.
    """
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler, status, body, content_type="text/plain; charset=utf-8"):
    """!
    @brief Send a text-based HTTP response.

    @param handler Active HTTP request handler.
    @param status HTTP status code.
    @param body Response body text.
    @param content_type MIME type for the outgoing response.
    """
    raw = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def parse_json_body(handler):
    """!
    @brief Parse the request body as JSON.

    @param handler Active HTTP request handler.
    @return Parsed JSON payload as a dictionary-like object.
    """
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def make_password_hash(password, salt=None):
    """!
    @brief Hash a password using PBKDF2-HMAC-SHA256.

    @param password Plain-text password.
    @param salt Optional salt value. A random salt is generated when omitted.
    @return Salt and digest joined by a `$` separator.
    """
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored_hash):
    """!
    @brief Compare a plain-text password to a stored password hash.

    @param password Plain-text password.
    @param stored_hash Stored `salt$digest` hash string.
    @return True when the password matches, otherwise False.
    """
    salt, digest = stored_hash.split("$", 1)
    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return hmac.compare_digest(computed, digest)


def db_connect():
    """!
    @brief Create a SQLite connection configured for row-based access.

    @return Open SQLite connection with `sqlite3.Row` row factory.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def seed_cases(conn):
    """!
    @brief Insert initial sample case records into an empty database.

    @param conn Open SQLite connection.
    """
    now = utc_now()
    rows = [
        (
            "UQS-2026-001",
            "Ali Hussain",
            "Fatema Ali",
            "Hussain Ali",
            "Mediation regarding marital reconciliation and maintenance expectations.",
            "Marital",
            "In-progress",
            "2026-03-20",
            "2026-03-22",
            "https://example.org/docs/1",
            "2026-04-12",
            None,
            "Moiz Coordinator",
            "High",
            now,
            now,
        ),
        (
            "UQS-2026-002",
            "Sakina Tai",
            "Yusuf Tai",
            "Burhan Tai",
            "Family inheritance share clarification and property allocation dispute.",
            "Inheritance",
            "New",
            "2026-03-28",
            "2026-04-02",
            "https://example.org/docs/2",
            "2026-04-20",
            None,
            "Zehra Counselor",
            "Medium",
            now,
            now,
        ),
        (
            "UQS-2026-003",
            "Mufaddal Traders",
            "Mufaddal Traders",
            "Saifee Supplies",
            "Pending payment conflict between two business partners.",
            "Business",
            "Resolved",
            "2026-02-14",
            "2026-02-15",
            "https://example.org/docs/3",
            "2026-03-01",
            "2026-02-27",
            "Abbas Mediator",
            "Critical",
            now,
            now,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO cases (
            case_id, applicant, complainant, respondent, summary, case_type, status,
            created_date, start_date, documents_link, due_date, completed_date,
            assignee, priority, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def init_db():
    """!
    @brief Initialize the SQLite database schema and seed default data.

    The function creates the database directory, creates tables if needed,
    seeds the default users, and inserts sample case data when the database
    starts empty.
    """
    DATA_DIR.mkdir(exist_ok=True)
    conn = db_connect()
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin', 'Editor', 'Viewer')),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            applicant TEXT NOT NULL,
            complainant TEXT NOT NULL,
            respondent TEXT NOT NULL,
            summary TEXT NOT NULL,
            case_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_date TEXT NOT NULL,
            start_date TEXT,
            documents_link TEXT,
            due_date TEXT,
            completed_date TEXT,
            assignee TEXT,
            priority TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
            FOREIGN KEY(author_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,
            due_date TEXT,
            assignee TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
        );
        """
    )
    cur.execute("SELECT COUNT(*) AS count FROM users")
    if cur.fetchone()["count"] == 0:
        now = utc_now()
        cur.executemany(
            """
            INSERT INTO users (username, full_name, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("admin", "System Administrator", make_password_hash("admin123"), "Admin", now),
                ("editor", "Case Editor", make_password_hash("editor123"), "Editor", now),
                ("viewer", "Case Viewer", make_password_hash("viewer123"), "Viewer", now),
            ],
        )
    cur.execute("SELECT COUNT(*) AS count FROM cases")
    if cur.fetchone()["count"] == 0:
        seed_cases(conn)
    conn.commit()
    conn.close()


def role_allows_write(role):
    """!
    @brief Check whether a role can modify case data.

    @param role Role name to evaluate.
    @return True for Admin and Editor roles, otherwise False.
    """
    return role in {"Admin", "Editor"}


def normalize_case_payload(payload):
    """!
    @brief Validate and normalize incoming case payload data.

    @param payload Raw request payload.
    @return Cleaned payload dictionary ready for database persistence.
    @throws ValueError Raised when required fields or enum values are invalid.
    """
    required = [
        "case_id",
        "applicant",
        "complainant",
        "respondent",
        "summary",
        "case_type",
        "status",
        "created_date",
        "priority",
    ]
    fields = {
        "case_id": (payload.get("case_id") or "").strip(),
        "applicant": (payload.get("applicant") or "").strip(),
        "complainant": (payload.get("complainant") or "").strip(),
        "respondent": (payload.get("respondent") or "").strip(),
        "summary": (payload.get("summary") or "").strip(),
        "case_type": (payload.get("case_type") or "").strip(),
        "status": (payload.get("status") or "").strip(),
        "created_date": (payload.get("created_date") or "").strip(),
        "start_date": (payload.get("start_date") or "").strip() or None,
        "documents_link": (payload.get("documents_link") or "").strip() or None,
        "due_date": (payload.get("due_date") or "").strip() or None,
        "completed_date": (payload.get("completed_date") or "").strip() or None,
        "assignee": (payload.get("assignee") or "").strip() or None,
        "priority": (payload.get("priority") or "").strip(),
    }
    missing = [field for field in required if not fields[field]]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if fields["case_type"] not in CASE_TYPES:
        raise ValueError("Invalid case type.")
    if fields["status"] not in CASE_STATUSES:
        raise ValueError("Invalid status.")
    if fields["priority"] not in PRIORITIES:
        raise ValueError("Invalid priority.")
    return fields


def row_to_case(row):
    """!
    @brief Convert a SQLite row into a plain dictionary.

    @param row SQLite row object.
    @return Dictionary representation of the row.
    """
    return {key: row[key] for key in row.keys()}


def get_case_detail(conn, case_pk):
    """!
    @brief Fetch a case together with its comments and subtasks.

    @param conn Open SQLite connection.
    @param case_pk Internal numeric case primary key.
    @return Dictionary with `case`, `comments`, and `subtasks`, or `None`.
    """
    case_row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_pk,)).fetchone()
    if not case_row:
        return None
    comments = conn.execute(
        """
        SELECT comments.id, comments.body, comments.created_at, users.full_name AS author_name
        FROM comments JOIN users ON users.id = comments.author_id
        WHERE case_id = ?
        ORDER BY comments.created_at DESC
        """,
        (case_pk,),
    ).fetchall()
    subtasks = conn.execute(
        """
        SELECT id, title, is_done, due_date, assignee, created_at, updated_at
        FROM subtasks WHERE case_id = ? ORDER BY created_at DESC
        """,
        (case_pk,),
    ).fetchall()
    return {
        "case": row_to_case(case_row),
        "comments": [dict(row) for row in comments],
        "subtasks": [dict(row) for row in subtasks],
    }


def build_case_filters(params):
    """!
    @brief Translate query parameters into SQL filters and values.

    Supported filters include text search, enum fields, and date ranges.

    @param params Parsed query-string parameter dictionary.
    @return Tuple of `(filters, values)` for SQL composition.
    """
    filters = []
    values = []
    for key in ["assignee", "case_type", "status", "priority"]:
        value = (params.get(key, [""])[0] or "").strip()
        if value:
            filters.append(f"{key} = ?")
            values.append(value)
    for key in DATE_FIELDS:
        start = (params.get(f"{key}_from", [""])[0] or "").strip()
        end = (params.get(f"{key}_to", [""])[0] or "").strip()
        if start:
            filters.append(f"COALESCE({key}, '') >= ?")
            values.append(start)
        if end:
            filters.append(f"COALESCE({key}, '') <= ?")
            values.append(end)
    search = (params.get("search", [""])[0] or "").strip()
    if search:
        filters.append("(case_id LIKE ? OR applicant LIKE ? OR complainant LIKE ? OR respondent LIKE ? OR summary LIKE ?)")
        values.extend([f"%{search}%"] * 5)
    return filters, values


class AppHandler(BaseHTTPRequestHandler):
    """!
    @brief HTTP request handler for static assets and JSON API endpoints.

    This handler manages:
    - authentication/session lookups
    - static page delivery
    - case CRUD operations
    - comments and subtasks
    - dashboard analytics and CSV export
    """
    server_version = "UmoorQaza/1.0"

    def do_OPTIONS(self):
        """!
        @brief Respond to CORS preflight requests.
        """
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.end_headers()

    def do_GET(self):
        """!
        @brief Handle incoming HTTP GET requests.
        """
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed)
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        """!
        @brief Handle incoming HTTP POST requests.
        """
        self.handle_api_post(urlparse(self.path))

    def do_PUT(self):
        """!
        @brief Handle incoming HTTP PUT requests.
        """
        self.handle_api_put(urlparse(self.path))

    def serve_static(self, path):
        """!
        @brief Serve static frontend assets from the `static` directory.

        @param path Requested URL path.
        """
        if path == "/":
            path = "/index.html"
        target = (STATIC_DIR / path.lstrip("/")).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists() or not target.is_file():
            text_response(self, 404, "Not found")
            return
        content_type = "text/plain; charset=utf-8"
        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        raw = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def get_current_user(self):
        """!
        @brief Resolve the currently authenticated user from the session cookie.

        @return Public user dictionary when authenticated, otherwise `None`.
        """
        raw_cookie = self.headers.get("Cookie")
        if not raw_cookie:
            return None
        jar = cookies.SimpleCookie()
        jar.load(raw_cookie)
        morsel = jar.get(SESSION_COOKIE)
        if not morsel:
            return None
        with SESSION_LOCK:
            return SESSIONS.get(morsel.value)

    def require_auth(self):
        """!
        @brief Ensure that the current request is authenticated.

        @return Authenticated user dictionary, or `None` after writing a 401 response.
        """
        user = self.get_current_user()
        if not user:
            json_response(self, 401, {"error": "Authentication required."})
            return None
        return user

    def require_write_access(self):
        """!
        @brief Ensure that the current user has write permissions.

        @return Authenticated user dictionary, or `None` after writing a 403/401 response.
        """
        user = self.require_auth()
        if not user:
            return None
        if not role_allows_write(user["role"]):
            json_response(self, 403, {"error": "You do not have permission to modify cases."})
            return None
        return user

    def handle_api_get(self, parsed):
        """!
        @brief Route API GET requests to the correct endpoint handler.

        @param parsed Parsed request URL.
        """
        if parsed.path == "/api/session":
            json_response(self, 200, {"user": self.get_current_user()})
            return
        if parsed.path == "/api/meta":
            user = self.require_auth()
            if not user:
                return
            conn = db_connect()
            users = conn.execute("SELECT id, username, full_name, role FROM users ORDER BY full_name").fetchall()
            conn.close()
            json_response(self, 200, {
                "case_types": CASE_TYPES,
                "statuses": CASE_STATUSES,
                "priorities": PRIORITIES,
                "roles": ROLES,
                "users": [dict(row) for row in users],
            })
            return
        if parsed.path == "/api/cases":
            if not self.require_auth():
                return
            self.list_cases(parsed)
            return
        if parsed.path.startswith("/api/cases/"):
            if not self.require_auth():
                return
            self.get_case(parsed.path)
            return
        if parsed.path == "/api/dashboard":
            if not self.require_auth():
                return
            self.get_dashboard(parsed)
            return
        if parsed.path == "/api/export.csv":
            if not self.require_auth():
                return
            self.export_csv(parsed)
            return
        json_response(self, 404, {"error": "Endpoint not found."})

    def handle_api_post(self, parsed):
        """!
        @brief Route API POST requests to the correct endpoint handler.

        @param parsed Parsed request URL.
        """
        if parsed.path == "/api/login":
            payload = parse_json_body(self)
            username = (payload.get("username") or "").strip()
            password = payload.get("password") or ""
            conn = db_connect()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            conn.close()
            if not user or not verify_password(password, user["password_hash"]):
                json_response(self, 401, {"error": "Invalid credentials."})
                return
            public_user = {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
            }
            token = secrets.token_urlsafe(32)
            with SESSION_LOCK:
                SESSIONS[token] = public_user
            body = json.dumps({"user": public_user}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}={token}; HttpOnly; Path=/; SameSite=Lax")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/logout":
            raw_cookie = self.headers.get("Cookie")
            if raw_cookie:
                jar = cookies.SimpleCookie()
                jar.load(raw_cookie)
                morsel = jar.get(SESSION_COOKIE)
                if morsel:
                    with SESSION_LOCK:
                        SESSIONS.pop(morsel.value, None)
            self.send_response(200)
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}=deleted; Path=/; Max-Age=0")
            self.end_headers()
            return
        if parsed.path == "/api/cases":
            if not self.require_write_access():
                return
            self.create_case()
            return
        if parsed.path.startswith("/api/cases/") and parsed.path.endswith("/comments"):
            user = self.require_write_access()
            if not user:
                return
            self.add_comment(parsed.path, user)
            return
        if parsed.path.startswith("/api/cases/") and parsed.path.endswith("/subtasks"):
            if not self.require_write_access():
                return
            self.add_subtask(parsed.path)
            return
        json_response(self, 404, {"error": "Endpoint not found."})

    def handle_api_put(self, parsed):
        """!
        @brief Route API PUT requests to the correct endpoint handler.

        @param parsed Parsed request URL.
        """
        if parsed.path.startswith("/api/cases/") and "/subtasks/" in parsed.path:
            if not self.require_write_access():
                return
            self.update_subtask(parsed.path)
            return
        if parsed.path.startswith("/api/cases/"):
            if not self.require_write_access():
                return
            self.update_case(parsed.path)
            return
        json_response(self, 404, {"error": "Endpoint not found."})

    def list_cases(self, parsed):
        """!
        @brief Return the filtered case list.

        @param parsed Parsed request URL containing query parameters.
        """
        params = parse_qs(parsed.query)
        filters, values = build_case_filters(params)
        query = "SELECT * FROM cases"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY COALESCE(due_date, '9999-12-31') ASC, created_date DESC"
        conn = db_connect()
        rows = conn.execute(query, values).fetchall()
        conn.close()
        json_response(self, 200, {"cases": [row_to_case(row) for row in rows]})

    def get_case(self, path):
        """!
        @brief Return a single case with comments and subtasks.

        @param path Request path containing the internal case identifier.
        """
        try:
            case_pk = int(path.rstrip("/").split("/")[-1])
        except ValueError:
            json_response(self, 400, {"error": "Invalid case id."})
            return
        conn = db_connect()
        payload = get_case_detail(conn, case_pk)
        conn.close()
        if not payload:
            json_response(self, 404, {"error": "Case not found."})
            return
        json_response(self, 200, payload)

    def create_case(self):
        """!
        @brief Create a new case from the request payload.
        """
        try:
            payload = normalize_case_payload(parse_json_body(self))
        except ValueError as exc:
            json_response(self, 400, {"error": str(exc)})
            return
        now = utc_now()
        conn = db_connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO cases (
                    case_id, applicant, complainant, respondent, summary, case_type, status,
                    created_date, start_date, documents_link, due_date, completed_date,
                    assignee, priority, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["case_id"], payload["applicant"], payload["complainant"], payload["respondent"],
                    payload["summary"], payload["case_type"], payload["status"], payload["created_date"],
                    payload["start_date"], payload["documents_link"], payload["due_date"], payload["completed_date"],
                    payload["assignee"], payload["priority"], now, now,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            json_response(self, 400, {"error": "Case ID already exists."})
            return
        payload = get_case_detail(conn, cur.lastrowid)
        conn.close()
        json_response(self, 201, payload)

    def update_case(self, path):
        """!
        @brief Update an existing case record.

        @param path Request path containing the internal case identifier.
        """
        try:
            case_pk = int(path.rstrip("/").split("/")[-1])
            payload = normalize_case_payload(parse_json_body(self))
        except ValueError as exc:
            json_response(self, 400, {"error": str(exc)})
            return
        conn = db_connect()
        existing = conn.execute("SELECT id FROM cases WHERE id = ?", (case_pk,)).fetchone()
        if not existing:
            conn.close()
            json_response(self, 404, {"error": "Case not found."})
            return
        try:
            conn.execute(
                """
                UPDATE cases
                SET case_id = ?, applicant = ?, complainant = ?, respondent = ?, summary = ?,
                    case_type = ?, status = ?, created_date = ?, start_date = ?, documents_link = ?,
                    due_date = ?, completed_date = ?, assignee = ?, priority = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["case_id"], payload["applicant"], payload["complainant"], payload["respondent"],
                    payload["summary"], payload["case_type"], payload["status"], payload["created_date"],
                    payload["start_date"], payload["documents_link"], payload["due_date"], payload["completed_date"],
                    payload["assignee"], payload["priority"], utc_now(), case_pk,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            json_response(self, 400, {"error": "Case ID already exists."})
            return
        payload = get_case_detail(conn, case_pk)
        conn.close()
        json_response(self, 200, payload)

    def add_comment(self, path, user):
        """!
        @brief Add a comment to a case.

        @param path Request path containing the case identifier.
        @param user Authenticated user creating the comment.
        """
        parts = path.split("/")
        try:
            case_pk = int(parts[3])
        except (IndexError, ValueError):
            json_response(self, 400, {"error": "Invalid case id."})
            return
        body = (parse_json_body(self).get("body") or "").strip()
        if not body:
            json_response(self, 400, {"error": "Comment body is required."})
            return
        conn = db_connect()
        if not conn.execute("SELECT id FROM cases WHERE id = ?", (case_pk,)).fetchone():
            conn.close()
            json_response(self, 404, {"error": "Case not found."})
            return
        conn.execute(
            "INSERT INTO comments (case_id, body, author_id, created_at) VALUES (?, ?, ?, ?)",
            (case_pk, body, user["id"], utc_now()),
        )
        conn.commit()
        payload = get_case_detail(conn, case_pk)
        conn.close()
        json_response(self, 201, payload)

    def add_subtask(self, path):
        """!
        @brief Add a subtask to a case.

        @param path Request path containing the case identifier.
        """
        parts = path.split("/")
        try:
            case_pk = int(parts[3])
        except (IndexError, ValueError):
            json_response(self, 400, {"error": "Invalid case id."})
            return
        payload = parse_json_body(self)
        title = (payload.get("title") or "").strip()
        if not title:
            json_response(self, 400, {"error": "Subtask title is required."})
            return
        now = utc_now()
        conn = db_connect()
        if not conn.execute("SELECT id FROM cases WHERE id = ?", (case_pk,)).fetchone():
            conn.close()
            json_response(self, 404, {"error": "Case not found."})
            return
        conn.execute(
            """
            INSERT INTO subtasks (case_id, title, is_done, due_date, assignee, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_pk, title, 1 if payload.get("is_done") else 0,
                (payload.get("due_date") or "").strip() or None,
                (payload.get("assignee") or "").strip() or None, now, now,
            ),
        )
        conn.commit()
        result = get_case_detail(conn, case_pk)
        conn.close()
        json_response(self, 201, result)

    def update_subtask(self, path):
        """!
        @brief Update an existing subtask.

        @param path Request path containing case and subtask identifiers.
        """
        parts = path.rstrip("/").split("/")
        try:
            case_pk = int(parts[3])
            subtask_pk = int(parts[5])
        except (IndexError, ValueError):
            json_response(self, 400, {"error": "Invalid subtask path."})
            return
        payload = parse_json_body(self)
        title = (payload.get("title") or "").strip()
        if not title:
            json_response(self, 400, {"error": "Subtask title is required."})
            return
        conn = db_connect()
        existing = conn.execute("SELECT id FROM subtasks WHERE id = ? AND case_id = ?", (subtask_pk, case_pk)).fetchone()
        if not existing:
            conn.close()
            json_response(self, 404, {"error": "Subtask not found."})
            return
        conn.execute(
            """
            UPDATE subtasks
            SET title = ?, is_done = ?, due_date = ?, assignee = ?, updated_at = ?
            WHERE id = ? AND case_id = ?
            """,
            (
                title,
                1 if payload.get("is_done") else 0,
                (payload.get("due_date") or "").strip() or None,
                (payload.get("assignee") or "").strip() or None,
                utc_now(),
                subtask_pk,
                case_pk,
            ),
        )
        conn.commit()
        result = get_case_detail(conn, case_pk)
        conn.close()
        json_response(self, 200, result)

    def get_dashboard(self, parsed):
        """!
        @brief Build dashboard summary statistics and chart datasets.

        @param parsed Parsed request URL containing optional filters.
        """
        params = parse_qs(parsed.query)
        filters, values = build_case_filters(params)
        query = "SELECT * FROM cases"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        conn = db_connect()
        rows = [row_to_case(row) for row in conn.execute(query, values).fetchall()]
        conn.close()

        def count_by(field):
            counts = {}
            for row in rows:
                label = row.get(field) or "Unassigned"
                counts[label] = counts.get(label, 0) + 1
            return [{"label": key, "value": counts[key]} for key in sorted(counts.keys())]

        monthly = {}
        today = datetime.now(UTC).date()
        overdue = 0
        due_soon = 0
        for row in rows:
            month_label = (row.get("start_date") or row.get("created_date") or "")[:7] or "Unknown"
            monthly[month_label] = monthly.get(month_label, 0) + 1
            due_date = row.get("due_date")
            if not due_date:
                continue
            try:
                delta = datetime.strptime(due_date, "%Y-%m-%d").date() - today
            except ValueError:
                continue
            if row.get("status") not in {"Resolved", "Dropped"}:
                if delta.days < 0:
                    overdue += 1
                elif delta.days <= 7:
                    due_soon += 1

        json_response(self, 200, {
            "summary": {
                "total_cases": len(rows),
                "open_cases": len([row for row in rows if row["status"] not in {"Resolved", "Dropped"}]),
                "overdue_cases": overdue,
                "due_within_7_days": due_soon,
            },
            "by_status": count_by("status"),
            "by_type": count_by("case_type"),
            "by_assignee": count_by("assignee"),
            "by_priority": count_by("priority"),
            "by_start_month": [{"label": key, "value": monthly[key]} for key in sorted(monthly.keys())],
        })

    def export_csv(self, parsed):
        """!
        @brief Export filtered case records as CSV.

        @param parsed Parsed request URL containing optional filters.
        """
        params = parse_qs(parsed.query)
        filters, values = build_case_filters(params)
        query = f"SELECT {', '.join(EXPORT_FIELDS)} FROM cases"
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_date DESC"
        conn = db_connect()
        rows = conn.execute(query, values).fetchall()
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(EXPORT_FIELDS)
        for row in rows:
            writer.writerow([row[field] for field in EXPORT_FIELDS])
        data = output.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="cases-export.csv"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def run():
    """!
    @brief Initialize the application and start the HTTP server.
    """
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", 8000), AppHandler)
    print("Umoor Qaza Saifee Nagar server running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    run()
