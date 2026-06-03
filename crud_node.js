/**
 * DynamoDB CRUD Operations — Node.js (AWS SDK v3)
 * Requires: @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb
 */

import {
  DynamoDBClient,
} from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  PutCommand,
  GetCommand,
  UpdateCommand,
  DeleteCommand,
  QueryCommand,
  TransactWriteCommand,
} from "@aws-sdk/lib-dynamodb";

const TABLE_NAME = "EcommerceTable";

const client    = new DynamoDBClient({ region: process.env.AWS_REGION ?? "us-east-1" });
const docClient = DynamoDBDocumentClient.from(client, {
  marshallOptions:   { removeUndefinedValues: true },
  unmarshallOptions: { wrapNumbers: false },
});

// ── CREATE ─────────────────────────────────────────────────────────────────

export async function createCustomer({ customerId, name, email, phone }) {
  await docClient.send(new PutCommand({
    TableName: TABLE_NAME,
    Item: {
      PK:          `CUSTOMER#${customerId}`,
      SK:          `PROFILE#${customerId}`,
      entity_type: "CUSTOMER",
      customer_id: customerId,
      name,
      email,
      phone,
      status:      "ACTIVE",
      created_at:  new Date().toISOString(),
      GSI1PK:      "STATUS#ACTIVE",
      GSI1SK:      `CUSTOMER#${customerId}`,
    },
    ConditionExpression: "attribute_not_exists(PK)",
  }));
  console.log(`Customer ${customerId} created.`);
}

// ── READ ───────────────────────────────────────────────────────────────────

export async function getCustomer(customerId) {
  const { Item } = await docClient.send(new GetCommand({
    TableName: TABLE_NAME,
    Key: {
      PK: `CUSTOMER#${customerId}`,
      SK: `PROFILE#${customerId}`,
    },
  }));
  return Item ?? null;
}

export async function getCustomerOrders(customerId) {
  const { Items } = await docClient.send(new QueryCommand({
    TableName:                 TABLE_NAME,
    KeyConditionExpression:    "PK = :pk AND begins_with(SK, :skPrefix)",
    ExpressionAttributeValues: {
      ":pk":       `CUSTOMER#${customerId}`,
      ":skPrefix": "ORDER#",
    },
  }));
  return Items ?? [];
}

// ── UPDATE ─────────────────────────────────────────────────────────────────

export async function updateCustomerEmail(customerId, newEmail) {
  const { Attributes } = await docClient.send(new UpdateCommand({
    TableName:                 TABLE_NAME,
    Key: {
      PK: `CUSTOMER#${customerId}`,
      SK: `PROFILE#${customerId}`,
    },
    ConditionExpression:       "attribute_exists(PK)",
    UpdateExpression:          "SET email = :email, updated_at = :ts",
    ExpressionAttributeValues: {
      ":email": newEmail,
      ":ts":    new Date().toISOString(),
    },
    ReturnValues: "UPDATED_NEW",
  }));
  return Attributes;
}

// ── DELETE ─────────────────────────────────────────────────────────────────

export async function deleteCustomer(customerId) {
  await docClient.send(new DeleteCommand({
    TableName:           TABLE_NAME,
    Key: {
      PK: `CUSTOMER#${customerId}`,
      SK: `PROFILE#${customerId}`,
    },
    ConditionExpression: "attribute_exists(PK)",
  }));
  console.log(`Customer ${customerId} deleted.`);
}

// ── TRANSACTION (atomic multi-item write) ──────────────────────────────────

export async function placeOrder({ customerId, orderId, items, total }) {
  await docClient.send(new TransactWriteCommand({
    TransactItems: [
      {
        Put: {
          TableName: TABLE_NAME,
          Item: {
            PK:          `CUSTOMER#${customerId}`,
            SK:          `ORDER#${orderId}`,
            entity_type: "ORDER",
            customer_id: customerId,
            order_id:    orderId,
            status:      "PROCESSING",
            total,
            item_count:  items.length,
            order_date:  new Date().toISOString(),
            GSI1PK:      "STATUS#PROCESSING",
            GSI1SK:      `ORDER#${orderId}`,
          },
          ConditionExpression: "attribute_not_exists(PK)",
        },
      },
      ...items.map((item) => ({
        Put: {
          TableName: TABLE_NAME,
          Item: {
            PK:           `ORDER#${orderId}`,
            SK:           `ITEM#${item.productId}`,
            entity_type:  "ORDER_ITEM",
            order_id:     orderId,
            product_id:   item.productId,
            product_name: item.name,
            quantity:     item.quantity,
            unit_price:   item.price,
            line_total:   item.quantity * item.price,
          },
        },
      })),
    ],
  }));
  console.log(`Order ${orderId} placed for customer ${customerId}.`);
}
