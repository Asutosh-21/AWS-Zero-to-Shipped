terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  required_version = ">= 1.6.0"
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" { default = "us-east-1" }
variable "project"    { default = "nutriroute" }
variable "env"        { default = "prod" }

locals {
  prefix = "${var.project}-${var.env}"
  tags   = { Project = var.project, Environment = var.env, Hackathon = "AWS-Zero-to-Shipped-2026" }
}

# ── DynamoDB Tables ──────────────────────────────────────────────────────────

resource "aws_dynamodb_table" "users" {
  name         = "${local.prefix}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "profileType"
  attribute {
    name = "userId"
    type = "S"
  }
  attribute {
    name = "profileType"
    type = "S"
  }
  tags = local.tags
}

resource "aws_dynamodb_table" "food_sources" {
  name         = "${local.prefix}-food-sources"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "zipCode"
  range_key    = "sourceId"
  attribute {
    name = "zipCode"
    type = "S"
  }
  attribute {
    name = "sourceId"
    type = "S"
  }
  attribute {
    name = "sourceType"
    type = "S"
  }
  attribute {
    name = "trustScore"
    type = "N"
  }
  global_secondary_index {
    name            = "byType-index"
    hash_key        = "sourceType"
    range_key       = "zipCode"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "byTrust-index"
    hash_key        = "zipCode"
    range_key       = "trustScore"
    projection_type = "ALL"
  }
  tags = local.tags
}

resource "aws_dynamodb_table" "inventory" {
  name         = "${local.prefix}-inventory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sourceId"
  range_key    = "itemCategory"
  attribute {
    name = "sourceId"
    type = "S"
  }
  attribute {
    name = "itemCategory"
    type = "S"
  }
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }
  tags = local.tags
}

resource "aws_dynamodb_table" "trust_scores" {
  name         = "${local.prefix}-trust-scores"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "sourceId"
  range_key    = "date"
  attribute {
    name = "sourceId"
    type = "S"
  }
  attribute {
    name = "date"
    type = "S"
  }
  tags = local.tags
}

resource "aws_dynamodb_table" "nutri_scores" {
  name         = "${local.prefix}-nutri-scores"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "weekOf"
  attribute {
    name = "userId"
    type = "S"
  }
  attribute {
    name = "weekOf"
    type = "S"
  }
  tags = local.tags
}

# ── S3 Buckets ───────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "food_images"   { bucket = "${local.prefix}-food-images-${data.aws_caller_identity.current.account_id}" }
resource "aws_s3_bucket" "meal_plans"    { bucket = "${local.prefix}-meal-plans-${data.aws_caller_identity.current.account_id}" }
resource "aws_s3_bucket" "usda_docs"     { bucket = "${local.prefix}-usda-docs-${data.aws_caller_identity.current.account_id}" }
resource "aws_s3_bucket" "user_uploads"  { bucket = "${local.prefix}-user-uploads-${data.aws_caller_identity.current.account_id}" }
resource "aws_s3_bucket" "pantry_photos" { bucket = "${local.prefix}-pantry-photos-${data.aws_caller_identity.current.account_id}" }

resource "aws_s3_bucket_lifecycle_configuration" "user_uploads_lifecycle" {
  bucket = aws_s3_bucket.user_uploads.id
  rule {
    id     = "expire-uploads"
    status = "Enabled"
    expiration { days = 1 }
    filter { prefix = "user-uploads/" }
  }
}

# ── SNS Topic ────────────────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name         = "${local.prefix}-alerts"
  display_name = "NutriRoute"
  tags         = local.tags
}

# ── EventBridge Rules ────────────────────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "pantry_check" {
  name                = "${local.prefix}-pantry-check"
  schedule_expression = "rate(30 minutes)"
  tags                = local.tags
}

resource "aws_cloudwatch_event_rule" "nutriscore_weekly" {
  name                = "${local.prefix}-nutriscore-weekly"
  schedule_expression = "cron(0 8 ? * SUN *)"
  tags                = local.tags
}

# ── IAM Role for Lambda ──────────────────────────────────────────────────────

resource "aws_iam_role" "lambda_role" {
  name = "${local.prefix}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_policies" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/AmazonLocationFullAccess",
    "arn:aws:iam::aws:policy/AmazonRekognitionFullAccess",
    "arn:aws:iam::aws:policy/AmazonTranscribeFullAccess",
    "arn:aws:iam::aws:policy/AmazonPollyFullAccess",
    "arn:aws:iam::aws:policy/TranslateFullAccess",
    "arn:aws:iam::aws:policy/AmazonSNSFullAccess",
    "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
    "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
  ])
  role       = aws_iam_role.lambda_role.name
  policy_arn = each.value
}

data "aws_caller_identity" "current" {}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "sns_topic_arn"          { value = aws_sns_topic.alerts.arn }
output "dynamodb_users_table"   { value = aws_dynamodb_table.users.name }
output "dynamodb_sources_table" { value = aws_dynamodb_table.food_sources.name }
output "s3_usda_docs_bucket"    { value = aws_s3_bucket.usda_docs.bucket }
output "lambda_role_arn"        { value = aws_iam_role.lambda_role.arn }
