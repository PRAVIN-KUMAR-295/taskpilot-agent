import sqlite3
import time
try:
    from tools.registry import default_registry
    from database.repositories import AgentActionRepository
except ImportError:
    from backend.tools.registry import default_registry
    from backend.database.repositories import AgentActionRepository



class ToolExecutor:
    """Executes the chosen pipeline of tools, records the audit trail, and handles errors gracefully."""

    @staticmethod
    def execute_pipeline(
        user_id: int,
        conn: sqlite3.Connection,
        pipeline: List[Dict[str, Any]],
        run_id: str
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for item in pipeline:
            tool_name = item.get("tool_name")
            params = item.get("params", {})
            action_name = params.get("action") or params.get("title") or tool_name

            start_t = time.time()
            try:
                tool_res = default_registry.execute(tool_name, user_id=user_id, conn=conn, **params)
                elapsed_ms = round((time.time() - start_t) * 1000, 2)

                status = "SUCCESS" if tool_res.success else "FAILED"
                action_record = AgentActionRepository.log(
                    conn=conn,
                    user_id=user_id,
                    run_id=run_id,
                    action_name=f"{tool_name}:{action_name}",
                    tool_name=tool_name,
                    input_data=params,
                    output_data=tool_res.to_dict(),
                    status=status,
                    verification_status="UNVERIFIED",
                    verification_details={"elapsed_ms": elapsed_ms}
                )

                results.append({
                    "action_id": action_record["id"],
                    "tool_name": tool_name,
                    "action_name": action_name,
                    "params": params,
                    "result": tool_res.to_dict(),
                    "status": status,
                    "elapsed_ms": elapsed_ms
                })

            except Exception as e:
                elapsed_ms = round((time.time() - start_t) * 1000, 2)
                err_msg = f"Tool '{tool_name}' encountered an error: {str(e)}"
                action_record = AgentActionRepository.log(
                    conn=conn,
                    user_id=user_id,
                    run_id=run_id,
                    action_name=f"{tool_name}:{action_name}",
                    tool_name=tool_name,
                    input_data=params,
                    output_data={"error": err_msg},
                    status="FAILED",
                    verification_status="FAILED",
                    verification_details={"error": str(e), "elapsed_ms": elapsed_ms}
                )
                results.append({
                    "action_id": action_record["id"],
                    "tool_name": tool_name,
                    "action_name": action_name,
                    "params": params,
                    "result": {"success": False, "error": err_msg, "message": err_msg},
                    "status": "FAILED",
                    "elapsed_ms": elapsed_ms
                })

        return results
