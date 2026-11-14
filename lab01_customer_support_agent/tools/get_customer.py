from data import CUSTOMERS, CUSTOMERS_BY_EMAIL
from helpers.tool_helpers import tool_description_template, Description

get_customer_schema = {
    "name": "get_customer",
    "description": tool_description_template(Description(
        intro="Look up a customer record by customer ID or email address. Returns name, email, account status, "
              "and tier.",
        when_to_use="FIRST, before any account action (refund, escalation) - identity must be verified before "
                    "process_refund.",
        when_to_not_use="To find orders (use lookup_order). Do not guess an ID or email - ask the customer.",
        input="Provide exactly ONE of customer_id or email.",
        example='{"customer_id": "CUST-1001"} or {"email": "maria.santos@example.com"}',
    )),
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
            }
        }
    }
}


def get_customer_handler(customer_id: str | None = None, email: str | None = None) -> dict:
    customer: dict | None = None

    if (customer_id is None) == (email is None):  # both missing or both provided
        return {
            "error": True,
            "errorCategory": "validation",
            "isRetryable": True,
            "message": "Provide exactly one of customer_id or email.",
        }

    if customer_id is not None:
        customer = CUSTOMERS.get(customer_id)
    elif email is not None:
        customer = CUSTOMERS_BY_EMAIL.get(email)

    if customer is None:
        lookup = f"ID {customer_id}" if customer_id else f"email {email}"
        return {
            "error": True,
            "errorCategory": "validation",
            "isRetryable": True,
            "message": f"No customer found for {lookup}",
        }

    return {
        "customer_id": customer["customer_id"],
        "name": customer["name"],
        "email": customer["email"],
        "account_status": customer["account_status"],
        "tier": customer["tier"],
    }
