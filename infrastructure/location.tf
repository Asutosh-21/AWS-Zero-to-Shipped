resource "aws_location_map" "main" {
  map_name    = "${local.prefix}-map"
  description = "NutriRoute navigation map"
  configuration { style = "VectorEsriNavigation" }
  tags = local.tags
}

resource "aws_location_route_calculator" "main" {
  calculator_name = "${local.prefix}-router"
  description     = "NutriRoute route calculator"
  data_source     = "Esri"
  tags            = local.tags
}

resource "aws_location_place_index" "main" {
  index_name  = "${local.prefix}-places"
  description = "NutriRoute place index for food source geocoding"
  data_source = "Esri"
  data_source_configuration { intended_use = "Storage" }
  tags = local.tags
}

resource "aws_location_geofence_collection" "main" {
  collection_name = "${local.prefix}-geofences"
  description     = "NutriRoute 2-mile radius alerts around users"
  tags            = local.tags
}

output "location_map_name"        { value = aws_location_map.main.map_name }
output "location_router_name"     { value = aws_location_route_calculator.main.calculator_name }
output "location_place_index"     { value = aws_location_place_index.main.index_name }
output "location_geofence_collection" { value = aws_location_geofence_collection.main.collection_name }
