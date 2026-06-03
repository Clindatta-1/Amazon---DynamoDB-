# Amazon---DynamoDB-

> A professional reference guide and working examples for building production-grade applications with Amazon DynamoDB — covering table design, data modelling, CRUD operations, indexing strategies, and best practices.

[![AWS](https://img.shields.io/badge/AWS-DynamoDB-orange?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/dynamodb/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green?logo=node.js)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


## What is DynamoDB?

**Amazon DynamoDB** is a fully managed, serverless, key-value and document NoSQL database designed for applications requiring single-digit millisecond performance at any scale. It is:

- **Serverless** — no infrastructure to provision or manage
- **Globally distributed** — supports multi-region active-active replication via Global Tables
- **Infinitely scalable** — handles millions of requests per second without manual intervention
- **Highly available** — 99.999% SLA with built-in multi-AZ replication

| Feature | DynamoDB | Traditional RDBMS |
|---|---|---|
| Schema | Flexible (schemaless) | Fixed (enforced) |
| Scaling | Horizontal (automatic) | Vertical (manual) |
| Joins | Not supported (by design) | Supported |
| Consistency | Eventual or strong | ACID |
| Latency | Single-digit milliseconds | Variable |
| Pricing | Per request / provisioned | Instance-based |

---

## Core Concepts

### Keys

| Term | Description |
|---|---|
| **Partition Key (PK)** | Mandatory. Determines the physical partition. Must be unique if used alone. |
| **Sort Key (SK)** | Optional. Combined with PK to form a composite primary key. Enables range queries. |
| **Primary Key** | Either PK alone (simple) or PK + SK (composite). Uniquely identifies every item. |

### Data Structures

| Term | Description |
|---|---|
| **Table** | Top-level container. DynamoDB has no concept of a database schema per table. |
| **Item** | A single record (equivalent to a row). Max size: **400 KB**. |
| **Attribute** | A key-value field within an item (equivalent to a column). Types: String, Number, Binary, Boolean, Null, List, Map, Set. |

### Access Patterns (design first!)

DynamoDB requires you to **define your access patterns before designing the schema**. Unlike SQL, you cannot query arbitrary columns efficiently after the fact.

---

## Dataset

The sample dataset is provided in [`data/`](data/) and represents a simplified **e-commerce platform** — a classic single-table design use case.

### [`data/items.json`](data/items.json)
Raw DynamoDB item format with all attribute types for direct import via `aws dynamodb batch-write-item`.

### [`data/items.csv`](data/items.csv)
Flattened tabular representation of the same items — useful for analysis in R, Python (pandas), or Excel.

### Entity Model

The sample data covers four entity types stored in a **single table** (`EcommerceTable`):

| Entity | PK | SK | Description |
|---|---|---|---|
| Customer | `CUSTOMER#<customerId>` | `PROFILE#<customerId>` | Customer profile |
| Order | `CUSTOMER#<customerId>` | `ORDER#<orderId>` | Order placed by a customer |
| Product | `PRODUCT#<productId>` | `METADATA#<productId>` | Product catalogue item |
| OrderItem | `ORDER#<orderId>` | `ITEM#<productId>` | Line item within an order |

This single-table design enables all of the following access patterns **without a scan**:

1. Get customer profile by ID
2. Get all orders for a customer
3. Get all items in an order
4. Get a product by ID
5. Get recent orders for a customer (using SK sort)

---

## Project Structure

```
aws-dynamodb-project/
├── data/
│   ├── items.csv              # Flattened sample data (tabular)
│   └── items.json             # DynamoDB batch-write format
├── examples/
│   ├── crud_node.js           # CRUD operations — Node.js (AWS SDK v3)
│   ├── crud_python.py         # CRUD operations — Python (boto3)
│   ├── query_patterns.js      # Advanced query patterns — Node.js
│   └── table_setup.json       # CreateTable request body
├── README.md
└── LICENSE
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| AWS Account | [Free tier](https://aws.amazon.com/free/) includes 25 GB storage + 200M requests/month |
| AWS CLI v2 | `aws --version` |
| Node.js 18+ | For JavaScript examples |
| Python 3.9+ | For Python examples |
| AWS SDK v3 | `npm install @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb` |
| boto3 | `pip install boto3` |

---

## Setup & Configuration

### 1. Configure AWS credentials

```bash
aws configure
# AWS Access Key ID:     <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region:        us-east-1
# Default output format: json
```

> **Security best practice:** Use IAM roles in production. Never hard-code credentials in application code. Use environment variables or AWS Secrets Manager.

### 2. Create the sample table

```bash
aws dynamodb create-table \
  --table-name EcommerceTable \
  --attribute-definitions \
      AttributeName=PK,AttributeType=S \
      AttributeName=SK,AttributeType=S \
  --key-schema \
      AttributeName=PK,KeyType=HASH \
      AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 3. Verify the table is active

```bash
aws dynamodb describe-table \
  --table-name EcommerceTable \
  --query "Table.TableStatus"
# Expected: "ACTIVE"
```

### 4. Load sample data

```bash
aws dynamodb batch-write-item \
  --request-items file://data/items.json
```

### 5. (Optional) Use DynamoDB Local for development

```bash
docker run -p 8000:8000 amazon/dynamodb-local
export AWS_ENDPOINT_URL=http://localhost:8000
```

---

## Table Design

### Single-Table Design (Recommended)

Single-table design stores all entities in one table, using composite key patterns and a Global Secondary Index (GSI) to support multiple access patterns efficiently.

```
┌────────────────────────────────┬──────────────────────────────────┬──────────────────┐
│ PK                             │ SK                               │ Attributes       │
├────────────────────────────────┼──────────────────────────────────┼──────────────────┤
│ CUSTOMER#C001                  │ PROFILE#C001                     │ name, email, ... │
│ CUSTOMER#C001                  │ ORDER#O1001                      │ total, status    │
│ CUSTOMER#C001                  │ ORDER#O1002                      │ total, status    │
│ ORDER#O1001                    │ ITEM#P001                        │ qty, price       │
│ ORDER#O1001                    │ ITEM#P002                        │ qty, price       │
│ PRODUCT#P001                   │ METADATA#P001                    │ name, price, ... │
└────────────────────────────────┴──────────────────────────────────┴──────────────────┘
```

### Key Design Rules

1. **Make keys descriptive** — prefix values with entity type (e.g. `CUSTOMER#`, `ORDER#`) to avoid key collisions between entity types.
2. **Sort key enables range queries** — `begins_with`, `between`, `>`, `<` all work on sort keys.
3. **Design for your read patterns** — model the table around how data is read, not how it is stored.

---

## CRUD Operations

### Node.js (AWS SDK v3)

```javascript
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand, GetCommand, UpdateCommand, DeleteCommand } from "@aws-sdk/lib-dynamodb";

const client = new DynamoDBClient({ region: "us-east-1" });
const docClient = DynamoDBDocumentClient.from(client);

// CREATE
await docClient.send(new PutCommand({
  TableName: "EcommerceTable",
  Item: {
    PK:        "CUSTOMER#C999",
    SK:        "PROFILE#C999",
    name:      "Jane Smith",
    email:     "jane@example.com",
    createdAt: new Date().toISOString(),
  },
  ConditionExpression: "attribute_not_exists(PK)", // Prevent overwrites
}));

// READ
const { Item } = await docClient.send(new GetCommand({
  TableName: "EcommerceTable",
  Key: { PK: "CUSTOMER#C999", SK: "PROFILE#C999" },
}));

// UPDATE
await docClient.send(new UpdateCommand({
  TableName: "EcommerceTable",
  Key: { PK: "CUSTOMER#C999", SK: "PROFILE#C999" },
  UpdateExpression:          "SET email = :email, updatedAt = :ts",
  ExpressionAttributeValues: { ":email": "new@example.com", ":ts": new Date().toISOString() },
  ReturnValues:              "UPDATED_NEW",
}));

// DELETE
await docClient.send(new DeleteCommand({
  TableName: "EcommerceTable",
  Key: { PK: "CUSTOMER#C999", SK: "PROFILE#C999" },
}));
```

### Python (boto3)

```python
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table    = dynamodb.Table("EcommerceTable")

# CREATE
table.put_item(
    Item={
        "PK":        "CUSTOMER#C999",
        "SK":        "PROFILE#C999",
        "name":      "Jane Smith",
        "email":     "jane@example.com",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    },
    ConditionExpression="attribute_not_exists(PK)",
)

# READ
response = table.get_item(Key={"PK": "CUSTOMER#C999", "SK": "PROFILE#C999"})
item = response.get("Item")

# UPDATE
table.update_item(
    Key={"PK": "CUSTOMER#C999", "SK": "PROFILE#C999"},
    UpdateExpression="SET email = :email, updatedAt = :ts",
    ExpressionAttributeValues={
        ":email": "new@example.com",
        ":ts":    datetime.now(timezone.utc).isoformat(),
    },
    ReturnValues="UPDATED_NEW",
)

# DELETE
table.delete_item(Key={"PK": "CUSTOMER#C999", "SK": "PROFILE#C999"})
```

---

## Query vs Scan

> **Rule of thumb:** Always use `Query`. Never use `Scan` in production unless absolutely necessary.

| Operation | How it works | Cost | Use when |
|---|---|---|---|
| `GetItem` | Exact key lookup | 1 RCU (eventually consistent) | You have both PK and SK |
| `Query` | Key condition on PK, optional SK expression | Reads only matching items | You have the PK and need to filter by SK |
| `Scan` | Reads **every item** in the table | Full table read — expensive | Data export, one-off migrations, testing only |

```javascript
// Query — get all orders for a customer (efficient)
const { Items } = await docClient.send(new QueryCommand({
  TableName:                 "EcommerceTable",
  KeyConditionExpression:    "PK = :pk AND begins_with(SK, :sk)",
  ExpressionAttributeValues: { ":pk": "CUSTOMER#C001", ":sk": "ORDER#" },
}));

// Filter — applied AFTER read; does NOT reduce read cost
const { Items } = await docClient.send(new QueryCommand({
  TableName:                 "EcommerceTable",
  KeyConditionExpression:    "PK = :pk AND begins_with(SK, :sk)",
  FilterExpression:          "#s = :status",
  ExpressionAttributeNames:  { "#s": "status" },
  ExpressionAttributeValues: { ":pk": "CUSTOMER#C001", ":sk": "ORDER#", ":status": "SHIPPED" },
}));
```

---

## Indexes (GSI & LSI)

### Global Secondary Index (GSI)

A GSI projects a **different PK and SK** over the same data, enabling queries on non-primary-key attributes.

```bash
aws dynamodb update-table \
  --table-name EcommerceTable \
  --attribute-definitions \
      AttributeName=GSI1PK,AttributeType=S \
      AttributeName=GSI1SK,AttributeType=S \
  --global-secondary-index-updates \
      "[{\"Create\":{\"IndexName\":\"GSI1\",
         \"KeySchema\":[{\"AttributeName\":\"GSI1PK\",\"KeyType\":\"HASH\"},
                        {\"AttributeName\":\"GSI1SK\",\"KeyType\":\"RANGE\"}],
         \"Projection\":{\"ProjectionType\":\"ALL\"},
         \"BillingMode\":\"PAY_PER_REQUEST\"}}]"
```

### Local Secondary Index (LSI)

An LSI shares the **same PK** but uses a **different SK**. Must be defined at table creation time. Useful for alternative sort orders.

### Index Comparison

| Feature | GSI | LSI |
|---|---|---|
| PK | Different from base table | Same as base table |
| Creation | Any time | Table creation only |
| Consistency | Eventual only | Eventual or strong |
| Limit | 20 per table | 5 per table |
| Storage | Separate | Shared with base table |

---

## Capacity Modes

### On-Demand (PAY_PER_REQUEST)

- Pay per request — no capacity planning needed
- Instantly scales to any traffic level
- **Best for:** unpredictable workloads, new applications, dev/test

### Provisioned

- Define Read Capacity Units (RCU) and Write Capacity Units (WCU) in advance
- Enable **Auto Scaling** to adjust automatically
- **Best for:** predictable, steady workloads where cost optimisation matters

| Unit | Definition |
|---|---|
| 1 RCU | 1 strongly consistent read (or 2 eventually consistent reads) of an item ≤ 4 KB/s |
| 1 WCU | 1 write of an item ≤ 1 KB/s |

---

## Best Practices

### Schema Design
- [ ] Define all access patterns **before** designing the table
- [ ] Use a **single-table design** where feasible to minimise operational overhead
- [ ] Prefix PK/SK values with entity type (e.g., `USER#`, `ORDER#`) to prevent collisions
- [ ] Use ISO 8601 timestamps in sort keys to enable time-range queries

### Performance
- [ ] Always use `Query` over `Scan` in production
- [ ] Use **sparse indexes** — only items with the GSI attribute are projected, keeping the index small
- [ ] Enable **DAX (DynamoDB Accelerator)** for microsecond read latency on hot data
- [ ] Use **batch operations** (`BatchGetItem`, `BatchWriteItem`) to reduce round-trips

### Reliability
- [ ] Use `ConditionExpression` on writes to implement optimistic locking and prevent overwrites
- [ ] Enable **Point-in-Time Recovery (PITR)** for all production tables
- [ ] Use **DynamoDB Streams** for event-driven architectures and cross-region replication
- [ ] Set **TTL (Time to Live)** on transient items (sessions, tokens, caches) to automate cleanup

### Security
- [ ] Apply least-privilege IAM policies — never use `dynamodb:*` in production
- [ ] Enable **encryption at rest** (enabled by default with AWS-managed keys)
- [ ] Use **VPC Endpoints** to keep traffic off the public internet
- [ ] Audit access with **AWS CloudTrail**

---

## Common Pitfalls

| Pitfall | Why it hurts | Fix |
|---|---|---|
| Using `Scan` in production | Reads entire table on every call; costs scale with data size | Redesign table to support `Query` |
| Hot partitions | All traffic hits a single partition key, causing throttling | Distribute writes across many PKs; add random suffix if needed |
| Over-indexing with GSIs | Each GSI replicates data and costs extra WCUs on every write | Only create indexes for actual access patterns |
| Storing large items | Items > 400 KB are rejected; large items increase RCU cost | Store large blobs in S3, store the S3 key in DynamoDB |
| Ignoring `FilterExpression` cost | Filter is applied after items are read; you still pay for all read items | Model the table so filtering is done via key conditions |
| Not using `ProjectionExpression` | GetItem/Query returns all attributes by default, increasing data transfer cost | Project only the attributes you need |

---

## Cost Estimation

Use the [AWS Pricing Calculator](https://calculator.aws/pricing/2/home) for accurate estimates. Quick reference:

| Resource | On-Demand Price (us-east-1) |
|---|---|
| Write Request Unit (WRU) | $1.25 per million |
| Read Request Unit (RRU) | $0.25 per million |
| Data storage | $0.25 per GB/month |
| Global Tables replication | $1.875 per million replicated WRUs |
| DAX | From $0.04/hour per node |
| Backups (PITR) | $0.20 per GB/month |

> **Free Tier (always free):** 25 GB storage, 25 WCU, 25 RCU (provisioned), 2.5M stream read requests/month.

---

