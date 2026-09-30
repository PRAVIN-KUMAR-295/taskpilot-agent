import sqlite3
import datetime
import json
import bcrypt

def create_tables(conn: sqlite3.Connection):
    """Creates all required tables for TaskPilot Agent."""
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        priority TEXT CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')) DEFAULT 'MEDIUM',
        status TEXT CHECK(status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')) DEFAULT 'TODO',
        due_date TEXT,
        estimated_duration INTEGER DEFAULT 30, -- in minutes
        category TEXT DEFAULT 'General',
        source TEXT DEFAULT 'user', -- 'user', 'agent', 'plan'
        dependencies TEXT DEFAULT '[]', -- JSON array of task IDs
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Reminders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER,
        title TEXT NOT NULL,
        reminder_time TEXT NOT NULL,
        status TEXT CHECK(status IN ('SCHEDULED', 'TRIGGERED', 'CANCELLED')) DEFAULT 'SCHEDULED',
        channel TEXT DEFAULT 'in_app', -- 'in_app', 'notification_tool', 'email_simulated'
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
    );
    """)

    # Schedules Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER,
        title TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        day_of_week TEXT,
        session_type TEXT DEFAULT 'focus', -- 'focus', 'study', 'meeting', 'review'
        is_optimized INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
    );
    """)

    # Plans Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal TEXT NOT NULL,
        status TEXT CHECK(status IN ('DRAFT', 'APPROVED', 'EXECUTED', 'REJECTED')) DEFAULT 'DRAFT',
        total_tasks INTEGER DEFAULT 0,
        estimated_days INTEGER DEFAULT 1,
        plan_data TEXT NOT NULL, -- JSON detailed breakdown
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Agent Runs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_runs (
        id TEXT PRIMARY KEY, -- UUID or custom run ID
        user_id INTEGER NOT NULL,
        goal TEXT NOT NULL,
        intent TEXT NOT NULL,
        status TEXT CHECK(status IN ('UNDERSTANDING', 'PLANNING', 'WAITING_FOR_APPROVAL', 'EXECUTING', 'VERIFYING', 'COMPLETED', 'FAILED')) DEFAULT 'UNDERSTANDING',
        requires_approval INTEGER DEFAULT 0,
        requires_approval_action TEXT, -- JSON action requiring confirmation
        summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Agent Actions (Audit Log) Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        user_id INTEGER NOT NULL,
        action_name TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        input_data TEXT DEFAULT '{}', -- JSON
        output_data TEXT DEFAULT '{}', -- JSON
        status TEXT CHECK(status IN ('SUCCESS', 'FAILED', 'PENDING', 'REJECTED')) DEFAULT 'SUCCESS',
        verification_status TEXT CHECK(verification_status IN ('VERIFIED', 'UNVERIFIED', 'FAILED')) DEFAULT 'VERIFIED',
        verification_details TEXT DEFAULT '{}', -- JSON
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (run_id) REFERENCES agent_runs(id) ON DELETE SET NULL
    );
    """)

    # Agent Memory Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        category TEXT DEFAULT 'preference', -- 'preference', 'habit', 'work_hours', 'constraint'
        source TEXT DEFAULT 'user_chat',
        confidence REAL DEFAULT 1.0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, key),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_user ON agent_actions(user_id, created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_user ON memory(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, status);")

    conn.commit()


def seed_default_data(conn: sqlite3.Connection):
    """Seeds default demo user, tasks, and memory if not present."""
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cursor.execute("SELECT id FROM users WHERE email = 'demo@taskpilot.ai'")
    row = cursor.fetchone()
    if not row:
        hashed = bcrypt.hashpw(b"demo123", bcrypt.gensalt()).decode("utf-8")
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("Hackathon Demo User", "demo@taskpilot.ai", hashed, now, now))
        user_id = cursor.lastrowid

        # Seed initial tasks
        initial_tasks = [
            ("Finalize AWS Architecture Diagram", "Complete cloud architecture overview with Bedrock and DynamoDB components", "HIGH", "IN_PROGRESS", "2026-10-02 18:00", 60, "Cloud", "agent"),
            ("Review Hackathon Presentation Pitch", "Polish slide deck, problem statement PS-01, and agent workflow", "URGENT", "TODO", "2026-10-01 20:00", 45, "Hackathon", "agent"),
            ("Test Autonomous Verification Flow", "Ensure all tool executions pass safety checks and post-condition verification", "HIGH", "TODO", "2026-10-02 12:00", 30, "Testing", "agent"),
            ("Set up Local Bedrock Mock Fallback", "Verify zero-key deterministic demo execution works reliably", "MEDIUM", "COMPLETED", "2026-09-30 15:00", 40, "Engineering", "user"),
            ("Configure Evening Focus Blocks", "Block 7:00 PM to 9:00 PM for deep study and coding sprint", "LOW", "TODO", "2026-10-03 21:00", 120, "Productivity", "user"),
        ]

        for title, desc, prio, stat, due, dur, cat, src in initial_tasks:
            cursor.execute("""
                INSERT INTO tasks (user_id, title, description, priority, status, due_date, estimated_duration, category, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, title, desc, prio, stat, due, dur, cat, src, now, now))

        # Seed initial memory preferences
        initial_memories = [
            ("preferred_working_hours", "09:00 AM - 06:00 PM", "work_hours", "user_profile"),
            ("preferred_evening_focus", "07:00 PM - 09:00 PM", "habit", "user_chat"),
            ("preferred_task_priority", "HIGH tasks tackled before noon", "preference", "user_chat"),
            ("preferred_study_duration", "45-60 minute deep focus intervals", "preference", "user_profile"),
            ("daily_planning_reminder", "08:30 AM every morning", "habit", "user_chat")
        ]

        for k, v, cat, src in initial_memories:
            cursor.execute("""
                INSERT INTO memory (user_id, key, value, category, source, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1.0, ?, ?)
            """, (user_id, k, v, cat, src, now, now))

        # Seed initial reminders
        cursor.execute("""
            INSERT INTO reminders (user_id, task_id, title, reminder_time, status, channel, created_at)
            VALUES (?, 2, 'Prepare PPT for Hackathon presentation', '2026-10-01 19:30', 'SCHEDULED', 'in_app', ?)
        """, (user_id, now))

        # Seed initial schedule
        cursor.execute("""
            INSERT INTO schedules (user_id, task_id, title, start_time, end_time, day_of_week, session_type, is_optimized, created_at)
            VALUES (?, 1, 'Deep Work: AWS Architecture', '09:00 AM', '10:30 AM', 'Tomorrow', 'focus', 1, ?)
        """, (user_id, now))

        # Seed initial audit action
        cursor.execute("""
            INSERT INTO agent_actions (user_id, action_name, tool_name, input_data, output_data, status, verification_status, verification_details, created_at)
            VALUES (?, 'System Initialized', 'SystemInit', '{}', '{"message": "TaskPilot environment initialized successfully"}', 'SUCCESS', 'VERIFIED', '{"check": "database_ready"}', ?)
        """, (user_id, now))

        conn.commit()
