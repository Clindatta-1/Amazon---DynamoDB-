"""
DynamoDB CRUD Operations — Python (boto3)
Requires: pip install boto3
"""

import os
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

TABLE_NAME = "EcommerceTable"

dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
table    = dynamodb.Table(TABLE_NAME)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── CREATE ─────────────────────────────────────────────────────────────────

def create_customer(customer_id: str, name: str, email: str, phone: str) -> None:
    try:
        table.put_item(
            Item={
                "PK":          f"CUSTOMER#{customer_id}",
                "SK":          f"PROFILE#{customer_id}",
                "entity_type": "CUSTOMER",
                "customer_id": customer_id,
                "name":        name,
                "email":       email,
                "phone":       phone,
                "status":      "ACTIVE",
                "created_at":  _now(),
                "GSI1PK":      "STATUS#ACTIVE",
                "GSI1SK":      f"CUSTOMER#{customer_id}",
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
        print(f"Customer {customer_id} created.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError(f"Customer {customer_id} already exists.") from e
        raise


# ── READ ───────────────────────────────────────────────────────────────────

def get_customer(customer_id: str) -> dict | None:
    response = table.get_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"PROFILE#{customer_id}"},
    )
    return response.get("Item")


def get_customer_orders(customer_id: str) -> list[dict]:
    response = table.query(
        KeyConditionExpression=(
            Key("PK").eq(f"CUSTOMER#{customer_id}") &
            Key("SK").begins_with("ORDER#")
        ),
    )
    return response.get("Items", [])


def get_orders_by_status(status: str) -> list[dict]:
    """Query via GSI1 — orders grouped by status."""
    response = table.query(
        IndexName="GSI1",
        KeyConditionExpression=(
            Key("GSI1PK").eq(f"STATUS#{status}") &
            Key("GSI1SK").begins_with("ORDER#")
        ),
    )
    return response.get("Items", [])


# ── UPDATE ─────────────────────────────────────────────────────────────────

def update_customer_email(customer_id: str, new_email: str) -> dict:
    response = table.update_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"PROFILE#{customer_id}"},
        ConditionExpression="attribute_exists(PK)",
        UpdateExpression="SET email = :email, updated_at = :ts",
        ExpressionAttributeValues={
            ":email": new_email,
            ":ts":    _now(),
        },
        ReturnValues="UPDATED_NEW",
    )
    return response.get("Attributes", {})


def update_order_status(order_id: str, customer_id: str, new_status: str) -> None:
    table.update_item(
        Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"ORDER#{order_id}"},
        UpdateExpression="SET #s = :status, GSI1PK = :gsi1pk, updated_at = :ts",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":status": new_status,
            ":gsi1pk": f"STATUS#{new_status}",
            ":ts":     _now(),
        },
    )


# ── DELETE ─────────────────────────────────────────────────────────────────

def delete_customer(customer_id: str) -> None:
    try:
        table.delete_item(
            Key={"PK": f"CUSTOMER#{customer_id}", "SK": f"PROFILE#{customer_id}"},
            ConditionExpression="attribute_exists(PK)",
        )
        print(f"Customer {customer_id} deleted.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError(f"Customer {customer_id} does not exist.") from e
        raise


# ── TRANSACTION ────────────────────────────────────────────────────────────

def place_order(customer_id: str, order_id: str, items: list[dict], total: float) -> None:
    """Atomically write an order header and all its line items."""
    client = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))

    transact_items = [
        {
            "Put": {
                "TableName": TABLE_NAME,
                "Item": {
                    "PK":          {"S": f"CUSTOMER#{customer_id}"},
                    "SK":          {"S": f"ORDER#{order_id}"},
                    "entity_type": {"S": "ORDER"},
                    "customer_id": {"S": customer_id},
                    "order_id":    {"S": order_id},
                    "status":      {"S": "PROCESSING"},
                    "total":       {"N": str(total)},
                    "item_count":  {"N": str(len(items))},
                    "order_date":  {"S": _now()},
                    "GSI1PK":      {"S": "STATUS#PROCESSING"},
                    "GSI1SK":      {"S": f"ORDER#{order_id}"},
                },
                "ConditionExpression": "attribute_not_exists(PK)",
            }
        },
        *[
            {
                "Put": {
                    "TableName": TABLE_NAME,
                    "Item": {
                        "PK":           {"S": f"ORDER#{order_id}"},
                        "SK":           {"S": f"ITEM#{item['product_id']}"},
                        "entity_type":  {"S": "ORDER_ITEM"},
                        "order_id":     {"S": order_id},
                        "product_id":   {"S": item["product_id"]},
                        "product_name": {"S": item["name"]},
                        "quantity":     {"N": str(item["quantity"])},
                        "unit_price":   {"N": str(item["price"])},
                        "line_total":   {"N": str(item["quantity"] * item["price"])},
                    },
                }
            }
            for item in items
        ],
    ]

    client.transact_write_items(TransactItems=transact_items)
    print(f"Order {order_id} placed for customer {customer_id}.")


# ── EXAMPLE USAGE ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_customer("C999", "Test User", "test@example.com", "+1-555-9999")

    customer = get_customer("C999")
    print("Customer:", customer)

    orders = get_customer_orders("C001")
    print(f"Customer C001 has {len(orders)} order(s).")

    place_order(
        customer_id="C999",
        order_id="O9001",
        items=[
            {"product_id": "P001", "name": "Wireless Headphones", "quantity": 1, "price": 49.99},
            {"product_id": "P003", "name": "Phone Stand",         "quantity": 2, "price": 10.00},
        ],
        total=69.99,
    )

    delete_customer("C999")
