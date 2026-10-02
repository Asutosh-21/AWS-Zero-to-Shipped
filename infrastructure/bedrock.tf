# ── Bedrock Knowledge Base ───────────────────────────────────────────────────

resource "aws_bedrockagent_knowledge_base" "main" {
  name        = "${local.prefix}-knowledge-base"
  description = "USDA nutrition data, SNAP guidelines, dietary rules"
  role_arn    = aws_iam_role.bedrock_agent_role.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }
  # Agent model: amazon.nova-lite-v1:0 (no approval needed, instant access)

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.main.arn
      vector_index_name = "nutriroute-index"
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }

  tags = local.tags
}

resource "aws_bedrockagent_data_source" "usda_docs" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
  name              = "usda-nutrition-docs"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.usda_docs.arn
    }
  }
}

# ── OpenSearch Serverless ────────────────────────────────────────────────────

resource "aws_opensearchserverless_collection" "main" {
  name = "${local.prefix}-food-search"
  type = "VECTORSEARCH"
  tags = local.tags
}

resource "aws_opensearchserverless_access_policy" "main" {
  name        = "${local.prefix}-access"
  type        = "data"
  description = "NutriRoute OpenSearch access"
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "index"
        Resource     = ["index/${local.prefix}-food-search/*"]
        Permission   = ["aoss:*"]
      },
      {
        ResourceType = "collection"
        Resource     = ["collection/${local.prefix}-food-search"]
        Permission   = ["aoss:*"]
      }
    ]
    Principal = [
      aws_iam_role.lambda_role.arn,
      aws_iam_role.bedrock_agent_role.arn,
    ]
  }])
}

resource "aws_opensearchserverless_security_policy" "encryption" {
  name   = "${local.prefix}-enc"
  type   = "encryption"
  policy = jsonencode({
    Rules  = [{ ResourceType = "collection", Resource = ["collection/${local.prefix}-food-search"] }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name   = "${local.prefix}-net"
  type   = "network"
  policy = jsonencode([{
    Rules = [
      { ResourceType = "collection", Resource = ["collection/${local.prefix}-food-search"] },
      { ResourceType = "dashboard",  Resource = ["collection/${local.prefix}-food-search"] }
    ]
    AllowFromPublic = true
  }])
}

# ── Bedrock Agent IAM Role ───────────────────────────────────────────────────

resource "aws_iam_role" "bedrock_agent_role" {
  name = "${local.prefix}-bedrock-agent-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "bedrock_agent_policies" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
    "arn:aws:iam::aws:policy/AWSLambdaRole",
  ])
  role       = aws_iam_role.bedrock_agent_role.name
  policy_arn = each.value
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "bedrock_kb_id"              { value = aws_bedrockagent_knowledge_base.main.id }
output "bedrock_kb_datasource_id"   { value = aws_bedrockagent_data_source.usda_docs.data_source_id }
output "opensearch_collection_arn"  { value = aws_opensearchserverless_collection.main.arn }
output "bedrock_agent_role_arn"     { value = aws_iam_role.bedrock_agent_role.arn }
