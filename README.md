<!-- PROJECT LOGO -->

<br />
<div align="center">

![Alt](https://image.pitchbook.com/eiElTAaD9aW5aDdCv0MZQp6Wcba1579025250555_200x200)

<h3 align="center">data/pipelines/lakehouse/core/event-bus-table-ddl-lambda</h3>


## About The Project

This Lambda function creates Apache Iceberg tables in the AWS Glue catalog using [PyIceberg](https://py.iceberg.apache.org/). It is deployed as a container image to avoid platform-specific binary mismatches (e.g. `pydantic_core`) that occur with zip-based Lambda packaging.

### Project contents

* `src/pyiceberg_make_table.py` contains the Lambda handler. It parses a JSON event into a PyIceberg `Schema`, optional `PartitionSpec`, and table properties, then calls `catalog.create_table()` against the Glue catalog.
* `Dockerfile` builds the Lambda container image on `public.ecr.aws/lambda/python:3.12`, installing dependencies via `uv` to `/opt/python`.
* `pyproject.toml` / `uv.lock` define Python dependencies (`pyiceberg`, `s3fs`, `pyarrow`).
* `Jenkinsfile` defines the CI/CD pipeline: targeted ECR/SSM apply, Docker image build/push via CodeBuild, then full Terraform plan/apply.
* `buildspec-push.yaml` builds the Docker image and pushes it to the build account ECR.
* `buildspec-pull.yaml` pulls the image from the build account ECR and pushes it to the target environment ECR.
* `tf/` holds the Terraform configuration for the Lambda, ECR, IAM, and SSM resources.
* `tf/deploy-build/` holds the Terraform configuration for the build account ECR repository.

<!-- GETTING STARTED -->

## Getting Started

### Prerequisites

* [UV](https://docs.astral.sh/uv/)
  ```sh
  brew install uv
  ```
* [pre-commit](https://pre-commit.com/)
  ```sh
  brew install pre-commit
  ```
* [Terraform](https://www.terraform.io/)
  ```sh
  brew install terraform
  ```
* Docker (for local testing and image builds)

### Bootstrap your local environment

From the repo root run:

```sh
uv sync
pre-commit install
```

## Usage

### Event payload

The Lambda expects a JSON event with the following structure:

```json
{
  "database": "my_database",
  "table_name": "my_table",
  "schema": [
    {"name": "id", "type": "long", "nullable": false, "comment": "Primary key"},
    {"name": "name", "type": "string", "nullable": true, "comment": "Customer name"},
    {"name": "created_at", "type": "timestamp", "nullable": true, "comment": "Record creation time"}
  ]
}
```

#### Required fields

| Field | Type | Description |
|---|---|---|
| `database` | `string` | Glue database name (must already exist) |
| `table_name` | `string` | Name for the new Iceberg table |
| `schema` | `array` | Column definitions (see below) |

#### Optional fields

| Field | Type | Default | Description |
|---|---|---|---|
| `region` | `string` | `eu-west-1` | AWS region for the Glue catalog |
| `warehouse` | `string` | `s3://dev-lakehouse-raw-zone/` | S3 warehouse path for table data |
| `location` | `string` | *derived from warehouse* | Explicit S3 location, overrides the warehouse-derived path |
| `description` | `string` | `""` | Table description |
| `partition_spec` | `array` | *none* | Partition definitions (see below) |
| `table_properties` | `object` | `{"write.format.default": "parquet", "write.parquet.compression-codec": "snappy"}` | Iceberg table properties (key-value pairs) |

### Schema columns

Each entry in the `schema` array is an object with:

| Key | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | yes | Column name |
| `type` | `string` | yes | Data type (see supported types) |
| `nullable` | `boolean` | no (default `true`) | Whether the column allows nulls |
| `comment` | `string` | no (default `""`) | Column description |

#### Supported types

**Primitives:** `string`, `long`, `int`/`integer`, `double`, `float`, `boolean`/`bool`, `date`, `timestamp`, `timestamptz`, `binary`

**Parameterised:** `decimal(precision, scale)`

**Complex:**
- `list<element_type>` or `array<element_type>` -- e.g. `list<string>`
- `map<key_type, value_type>` -- e.g. `map<string, long>`
- `struct<field1:type1, field2:type2>` -- e.g. `struct<street:string, city:string, zip:string>`

Complex types can be nested: `list<struct<name:string, value:int>>`

### Partition spec

Each entry in the `partition_spec` array is an object with:

| Key | Type | Required | Description |
|---|---|---|---|
| `source_field` | `string` | yes | Name of a column from the schema to partition on |
| `transform` | `string` | yes | Partition transform to apply |
| `name` | `string` | no | Partition field name (defaults to `{source_field}_{transform}`) |

#### Supported transforms

| Transform | Description | Example |
|---|---|---|
| `identity` | Partition by the raw value | `{"source_field": "region", "transform": "identity"}` |
| `day` | Partition by day (from a date/timestamp column) | `{"source_field": "created_at", "transform": "day"}` |
| `month` | Partition by month | `{"source_field": "created_at", "transform": "month"}` |
| `year` | Partition by year | `{"source_field": "created_at", "transform": "year"}` |
| `hour` | Partition by hour | `{"source_field": "created_at", "transform": "hour"}` |
| `bucket[N]` | Hash partition into N buckets | `{"source_field": "id", "transform": "bucket[16]"}` |
| `truncate[N]` | Truncate to width N | `{"source_field": "name", "transform": "truncate[4]"}` |

### Table properties

The `table_properties` object is passed directly to Iceberg as table-level key-value metadata. Use it for Iceberg write settings and any custom metadata you need to attach to the table.

```json
{
  "table_properties": {
    "write.format.default": "parquet",
    "write.parquet.compression-codec": "snappy",
    "write.target-file-size-bytes": "536870912",
    "s3_source_bucket": "dev-lakehouse-landing-zone",
    "s3_source_prefix": "my_database/my_table/",
    "target_firehose_stream": "dev-my-firehose-stream"
  }
}
```

### Full example payload

```json
{
  "database": "dev_dcx_new_originations",
  "table_name": "customer_events",
  "description": "Customer origination events",
  "region": "eu-west-1",
  "warehouse": "s3://dev-lakehouse-raw-zone/",
  "location": "s3://dev-lakehouse-raw-zone/dev_dcx_new_originations/customer_events/",
  "schema": [
    {"name": "client_guid", "type": "string", "nullable": true, "comment": "Client identifier"},
    {"name": "connector_id", "type": "long", "nullable": true, "comment": "Connector ID"},
    {"name": "created_at", "type": "timestamp", "nullable": true, "comment": "Event timestamp"},
    {"name": "tags", "type": "list<string>", "nullable": true, "comment": "Tags list"},
    {"name": "address", "type": "struct<street:string,city:string,zip:string>", "nullable": true, "comment": "Address"},
    {"name": "metadata", "type": "map<string,string>", "nullable": true, "comment": "Metadata map"},
    {"name": "amount", "type": "decimal(10,2)", "nullable": true, "comment": "Amount"}
  ],
  "partition_spec": [
    {"source_field": "created_at", "transform": "day", "name": "day"}
  ],
  "table_properties": {
    "write.format.default": "parquet",
    "write.parquet.compression-codec": "snappy",
    "s3_source_bucket": "dev-lakehouse-landing-zone",
    "s3_source_prefix": "dev_dcx_new_originations/customer_events/"
  }
}
```

### Local testing with Docker

Build and run the Lambda container locally:

```sh
docker buildx build --platform linux/amd64 -t table-ddl-lambda .

docker run -p 9000:8080 \
  -e ENVIRONMENT=dev \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e AWS_SESSION_TOKEN=... \
  table-ddl-lambda
```

Invoke via the Lambda Runtime Interface Emulator:

```sh
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"database":"my_db","table_name":"test","schema":[{"name":"id","type":"long"}]}'
```

Or verify imports work without invoking:

```sh
docker run --rm --entrypoint python table-ddl-lambda \
  -c "from pyiceberg_make_table import lambda_handler; print('All imports successful')"
```

## CI/CD pipeline

The Jenkins pipeline expects two parameters:

* `env` -- one of `build`, `dev`, `test`, or `prod`.
* `tfAction` -- `plan`, `apply`, or `destroy`.

Pipeline stages:

1. **Initialising Backend** -- `terraform init` with the correct backend config.
2. **Targeted Plan/Apply - ECR + SSM** -- creates the ECR repository and SSM parameter before the image is pushed.
3. **Build and Push** (build env only) -- uses CodeBuild to build the Docker image and push to the build account ECR.
4. **Pull and Push** (dev/test/prod) -- pulls the image from the build account ECR and pushes to the target environment ECR via cross-account role assumption.
5. **Terraform Plan** -- full plan including the Lambda function referencing the pushed image.
6. **Terraform Apply/Destroy** -- gated with a manual approval step and a 10-minute timeout.
7. **Tag Release** -- tags the git commit on prod apply from master.

### Terraform configuration

* `tf/deploy-build/` -- build account resources (ECR repo, SSM param for ECR URL).
* `tf/` -- environment resources (Lambda, ECR repo, SSM param, IAM policies).
* `tf/config/<env>/` -- per-environment backend and variable files.
* `tf/config/common.tfvars` -- shared variables across environments.

## Testing

```sh
uv sync --group test
uv run pytest
```

<!-- CONTACT -->

## Contact

datapipelines@theverygroup.com
