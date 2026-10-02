# Re-export all DynamoDB table names as outputs for other modules

output "table_users_name"       { value = aws_dynamodb_table.users.name }
output "table_sources_name"     { value = aws_dynamodb_table.food_sources.name }
output "table_inventory_name"   { value = aws_dynamodb_table.inventory.name }
output "table_trust_name"       { value = aws_dynamodb_table.trust_scores.name }
output "table_nutri_name"       { value = aws_dynamodb_table.nutri_scores.name }

# Lambda environment variable block — paste into each Lambda config
# DYNAMODB_TABLE_USERS     = nutriroute-prod-users
# DYNAMODB_TABLE_SOURCES   = nutriroute-prod-food-sources
# DYNAMODB_TABLE_INVENTORY = nutriroute-prod-inventory
# DYNAMODB_TABLE_TRUST     = nutriroute-prod-trust-scores
# DYNAMODB_TABLE_NUTRI     = nutriroute-prod-nutri-scores
