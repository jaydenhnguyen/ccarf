from core.tools.errors import BUSINESS
from core.tools.results import ToolResult
from session import AgentSession


def add_found_order_to_case_facts(tool_result: ToolResult, session: AgentSession) -> None:
    content = tool_result["content"]
    if tool_result["is_error"] or not content["found"]:
        return

    orders = session.case_facts.orders
    order_id_from_tool_result = content["order_id"]

    entry = orders.get(order_id_from_tool_result)
    if entry is None:  # add order if it is not in the case_facts
        orders[order_id_from_tool_result] = {"total": content["total"], "status": content["status"]}
    else:
        entry["total"] = content["total"]
        entry["status"] = content["status"]


def add_refund_to_case_facts(tool_result: ToolResult, session: AgentSession) -> None:
    content = tool_result["content"]
    orders = session.case_facts.orders

    if not tool_result["is_error"] and content["is_refunded"]:
        entry = orders.setdefault(content["order_id"], {"total": content["order_total"], "status": "delivered"})
        entry["refunded"] = round(entry.get("refunded", 0) + content["amount"], 2)
        entry.setdefault("refund_ids", []).append(content["refund_id"])
        entry.pop("refund_blocked", None)  # resolved - collapse it
    elif tool_result["error_category"] == BUSINESS and content.get("order_id") in orders:
        orders[content["order_id"]]["refund_blocked"] = content["message"]


def add_escalation_to_case_facts(tool_result: ToolResult, session: AgentSession) -> None:
    if tool_result["is_error"]:
        return
    content = tool_result["content"]

    session.case_facts.escalation = {
        "escalation_id": content["escalation_id"],
        "escalation_type": content["escalation_type"],
    }
