import re

from config import SIMULATE_CUSTOMER_TIMEOUT
from context import ToolContext
from core.tools.description import Description, tool_description_template
from core.tools.errors import ToolTransientError, ToolValidationError
from core.tools.results import ToolResult
from core.tools.retry import RetryPolicy
from data import CUSTOMERS, CUSTOMERS_BY_EMAIL
from hooks.identity import add_verified_customer_record_to_case_facts

get_customer_schema = {
    "name": "get_customer",
    "description": tool_description_template(
        Description(
            intro="Look up a customer record by customer ID or email address.",
            when_to_use="FIRST, before lookup_order or process_refund - both require a verified customer in this "
            "conversation.",
            when_to_not_use="To find orders (use lookup_order). Do not guess an ID or email - ask the customer.",
            returns_success="found=true plus customer_id, name, email, account_status, tier. The customer is now "
            "verified for this conversation. If account_status is not 'active', refunds will be blocked; explain and "
            "offer to escalate.",
            returns_empty="found=false - no customer matches that ID/email. Not a failure: do not retry with the same "
            "value; ask the customer to re-check it or offer the other identifier.",
            returns_error="is_error - validation: invalid input (neither or both identifiers, or a malformed "
            "value); fix it or ask the customer. transient: the lookup did not complete - do NOT say "
            "the customer doesn't exist.",
            input="Provide exactly ONE of customer_id or email.",
            example='{"customer_id": "CUST-1001"} or {"email": "maria.santos@example.com"}',
        )
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "string",
                "description": "The customer ID (e.g., 'CUST-1001'). Provide this OR email, not both.",
            },
            "email": {
                "type": "string",
                "description": "The customer's email address. Provide this OR customer_id, not both.",
            },
        },
    },
}

get_customer_retry_policy: RetryPolicy = {"retry_by": "code", "max_attempts": 3}

# order matter
get_customer_post_hooks = [add_verified_customer_record_to_case_facts]

CUSTOMER_ID_PATTERN = re.compile(r"^CUST-\d{4}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_customer_handler(_ctx: ToolContext, customer_id: str | None = None, email: str | None = None) -> ToolResult:
    if (customer_id is None) == (email is None):
        raise ToolValidationError("Provide exactly one of customer_id or email, not both or neither.")

    if customer_id is not None and not CUSTOMER_ID_PATTERN.match(customer_id):
        raise ToolValidationError(
            "customer_id must look like 'CUST-1234'. Ask the customer to re-check it.", customer_id=customer_id
        )
    if email is not None and not EMAIL_PATTERN.match(email):
        raise ToolValidationError("email is not a valid address. Ask the customer to re-check it.", email=email)

    lookup_key, value = ("customer_id", customer_id) if customer_id else ("email", email)

    if SIMULATE_CUSTOMER_TIMEOUT:
        raise ToolTransientError("Customer DB query timed out.", **{lookup_key: value})

    customer = CUSTOMERS.get(customer_id) if customer_id else CUSTOMERS_BY_EMAIL.get(email)

    if customer is None:
        return {
            "is_error": False,
            "content": {"found": False, lookup_key: value, "message": f"No customer found for {lookup_key}: {value}"},
        }

    return {
        "is_error": False,
        "content": {
            "found": True,
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "email": customer["email"],
            "account_status": customer["account_status"],
            "tier": customer["tier"],
        },
    }
