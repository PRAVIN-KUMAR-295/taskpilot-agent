import json
import sqlite3
import datetime
from typing import List, Optional, Dict, Any

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class UserRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_email(conn: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(conn: sqlite3.Connection, name: str, email: str, password_hash: str) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name.strip(), email.strip().lower(), password_hash, now, now))
        conn.commit()
        return UserRepository.get_by_id(conn, cursor.lastrowid)


class TaskRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, task_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        else:
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def list_all(
        conn: sqlite3.Connection,
        user_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = "SELECT * FROM tasks WHERE user_id = ?"
        params: List[Any] = [user_id]

        if status:
            query += " AND status = ?"
            params.append(status.upper())
        if priority:
            query += " AND priority = ?"
            params.append(priority.upper())
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY CASE priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 WHEN 'LOW' THEN 4 ELSE 5 END, id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def create(
        conn: sqlite3.Connection,
        user_id: int,
        title: str,
        description: str = "",
        priority: str = "MEDIUM",
        status: str = "TODO",
        due_date: Optional[str] = None,
        estimated_duration: int = 30,
        category: str = "General",
        source: str = "user",
        dependencies: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        dep_json = json.dumps(dependencies or [])
        cursor.execute("""
            INSERT INTO tasks (
                user_id, title, description, priority, status, due_date,
                estimated_duration, category, source, dependencies, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, title.strip(), description.strip(), priority.upper(),
            status.upper(), due_date, estimated_duration, category.strip(),
            source, dep_json, now, now
        ))
        conn.commit()
        return TaskRepository.get_by_id(conn, cursor.lastrowid)

    @staticmethod
    def update(
        conn: sqlite3.Connection,
        task_id: int,
        user_id: int,
        **updates: Any
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        allowed = {
            "title", "description", "priority", "status",
            "due_date", "estimated_duration", "category", "source", "dependencies"
        }
        fields = []
        params = []
        for k, v in updates.items():
            if k in allowed and v is not None:
                if k == "priority":
                    v = str(v).upper()
                elif k == "status":
                    v = str(v).upper()
                elif k == "dependencies" and isinstance(v, list):
                    v = json.dumps(v)
                fields.append(f"{k} = ?")
                params.append(v)

        if not fields:
            return TaskRepository.get_by_id(conn, task_id, user_id)

        fields.append("updated_at = ?")
        params.append(_now())
        params.extend([task_id, user_id])

        cursor.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ? AND user_id = ?", params)
        conn.commit()
        return TaskRepository.get_by_id(conn, task_id, user_id)

    @staticmethod
    def complete(conn: sqlite3.Connection, task_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        return TaskRepository.update(conn, task_id, user_id, status="COMPLETED")

    @staticmethod
    def delete(conn: sqlite3.Connection, task_id: int, user_id: int) -> bool:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def clear_all(conn: sqlite3.Connection, user_id: int) -> int:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount


class ReminderRepository:
    @staticmethod
    def list_by_user(conn: sqlite3.Connection, user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM reminders WHERE user_id = ? AND status = ? ORDER BY id DESC", (user_id, status.upper()))
        else:
            cursor.execute("SELECT * FROM reminders WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def create(
        conn: sqlite3.Connection,
        user_id: int,
        title: str,
        reminder_time: str,
        task_id: Optional[int] = None,
        channel: str = "in_app"
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        cursor.execute("""
            INSERT INTO reminders (user_id, task_id, title, reminder_time, status, channel, created_at)
            VALUES (?, ?, ?, ?, 'SCHEDULED', ?, ?)
        """, (user_id, task_id, title, reminder_time, channel, now))
        conn.commit()
        cursor.execute("SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,))
        return dict(cursor.fetchone())

    @staticmethod
    def cancel(conn: sqlite3.Connection, reminder_id: int, user_id: int) -> bool:
        cursor = conn.cursor()
        cursor.execute("UPDATE reminders SET status = 'CANCELLED' WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


class ScheduleRepository:
    @staticmethod
    def list_by_user(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedules WHERE user_id = ? ORDER BY id ASC", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def create(
        conn: sqlite3.Connection,
        user_id: int,
        title: str,
        start_time: str,
        end_time: str,
        task_id: Optional[int] = None,
        day_of_week: Optional[str] = None,
        session_type: str = "focus",
        is_optimized: int = 0
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        cursor.execute("""
            INSERT INTO schedules (user_id, task_id, title, start_time, end_time, day_of_week, session_type, is_optimized, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, task_id, title, start_time, end_time, day_of_week or "Today", session_type, is_optimized, now))
        conn.commit()
        cursor.execute("SELECT * FROM schedules WHERE id = ?", (cursor.lastrowid,))
        return dict(cursor.fetchone())

    @staticmethod
    def clear_by_user(conn: sqlite3.Connection, user_id: int) -> int:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM schedules WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount


class PlanRepository:
    @staticmethod
    def create(
        conn: sqlite3.Connection,
        user_id: int,
        goal: str,
        plan_data: Dict[str, Any],
        status: str = "DRAFT",
        total_tasks: int = 0,
        estimated_days: int = 1
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        cursor.execute("""
            INSERT INTO plans (user_id, goal, status, total_tasks, estimated_days, plan_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, goal, status, total_tasks, estimated_days, json.dumps(plan_data), now))
        conn.commit()
        cursor.execute("SELECT * FROM plans WHERE id = ?", (cursor.lastrowid,))
        row = dict(cursor.fetchone())
        row["plan_data"] = json.loads(row["plan_data"])
        return row

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, plan_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["plan_data"] = json.loads(res["plan_data"])
        return res

    @staticmethod
    def list_by_user(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM plans WHERE user_id = ? ORDER BY id DESC", (user_id,))
        items = []
        for row in cursor.fetchall():
            d = dict(row)
            try:
                d["plan_data"] = json.loads(d["plan_data"])
            except Exception:
                pass
            items.append(d)
        return items

    @staticmethod
    def update_status(conn: sqlite3.Connection, plan_id: int, user_id: int, status: str) -> bool:
        cursor = conn.cursor()
        cursor.execute("UPDATE plans SET status = ? WHERE id = ? AND user_id = ?", (status, plan_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


class AgentRunRepository:
    @staticmethod
    def create(
        conn: sqlite3.Connection,
        run_id: str,
        user_id: int,
        goal: str,
        intent: str,
        status: str = "UNDERSTANDING",
        requires_approval: bool = False,
        requires_approval_action: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        act_json = json.dumps(requires_approval_action) if requires_approval_action else None
        cursor.execute("""
            INSERT INTO agent_runs (id, user_id, goal, intent, status, requires_approval, requires_approval_action, summary, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                summary = excluded.summary,
                requires_approval = excluded.requires_approval,
                requires_approval_action = excluded.requires_approval_action,
                updated_at = excluded.updated_at
        """, (run_id, user_id, goal, intent, status, 1 if requires_approval else 0, act_json, summary, now, now))
        conn.commit()
        return AgentRunRepository.get_by_id(conn, run_id)


    @staticmethod
    def get_by_id(conn: sqlite3.Connection, run_id: str) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("requires_approval_action"):
            try:
                res["requires_approval_action"] = json.loads(res["requires_approval_action"])
            except Exception:
                pass
        res["requires_approval"] = bool(res["requires_approval"])
        return res

    @staticmethod
    def update(
        conn: sqlite3.Connection,
        run_id: str,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        requires_approval: Optional[bool] = None,
        requires_approval_action: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        fields = ["updated_at = ?"]
        params: List[Any] = [_now()]

        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if summary is not None:
            fields.append("summary = ?")
            params.append(summary)
        if requires_approval is not None:
            fields.append("requires_approval = ?")
            params.append(1 if requires_approval else 0)
        if requires_approval_action is not None:
            fields.append("requires_approval_action = ?")
            params.append(json.dumps(requires_approval_action))

        params.append(run_id)
        cursor.execute(f"UPDATE agent_runs SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        return AgentRunRepository.get_by_id(conn, run_id)


class AgentActionRepository:
    @staticmethod
    def log(
        conn: sqlite3.Connection,
        user_id: int,
        action_name: str,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        status: str = "SUCCESS",
        verification_status: str = "VERIFIED",
        verification_details: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        cursor.execute("""
            INSERT INTO agent_actions (
                run_id, user_id, action_name, tool_name, input_data,
                output_data, status, verification_status, verification_details, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, user_id, action_name, tool_name,
            json.dumps(input_data), json.dumps(output_data),
            status, verification_status,
            json.dumps(verification_details or {}), now
        ))
        conn.commit()
        cursor.execute("SELECT * FROM agent_actions WHERE id = ?", (cursor.lastrowid,))
        row = dict(cursor.fetchone())
        row["input_data"] = json.loads(row["input_data"])
        row["output_data"] = json.loads(row["output_data"])
        row["verification_details"] = json.loads(row["verification_details"])
        return row

    @staticmethod
    def list_by_user(conn: sqlite3.Connection, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agent_actions WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        results = []
        for r in cursor.fetchall():
            d = dict(r)
            try:
                d["input_data"] = json.loads(d["input_data"])
                d["output_data"] = json.loads(d["output_data"])
                d["verification_details"] = json.loads(d["verification_details"])
            except Exception:
                pass
            results.append(d)
        return results


class MemoryRepository:
    @staticmethod
    def get_all(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memory WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def set(
        conn: sqlite3.Connection,
        user_id: int,
        key: str,
        value: str,
        category: str = "preference",
        source: str = "user_chat",
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        now = _now()
        cursor.execute("""
            INSERT INTO memory (user_id, key, value, category, source, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                source = excluded.source,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
        """, (user_id, key.strip(), value.strip(), category, source, confidence, now, now))
        conn.commit()
        cursor.execute("SELECT * FROM memory WHERE user_id = ? AND key = ?", (user_id, key.strip()))
        return dict(cursor.fetchone())

    @staticmethod
    def delete(conn: sqlite3.Connection, memory_id: int, user_id: int) -> bool:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory WHERE id = ? AND user_id = ?", (memory_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def clear_all(conn: sqlite3.Connection, user_id: int) -> int:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount
