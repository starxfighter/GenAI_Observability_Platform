# Kinesis Module - Outputs

output "events_stream_name" {
  description = "Events stream name"
  value       = aws_kinesis_stream.events.name
}

output "events_stream_arn" {
  description = "Events stream ARN"
  value       = aws_kinesis_stream.events.arn
}

output "firehose_delivery_stream_name" {
  description = "Firehose delivery stream name"
  value       = aws_kinesis_firehose_delivery_stream.s3.name
}

output "firehose_delivery_stream_arn" {
  description = "Firehose delivery stream ARN"
  value       = aws_kinesis_firehose_delivery_stream.s3.arn
}

output "consumer_arn" {
  description = "Enhanced fan-out consumer ARN"
  value       = var.enable_enhanced_fanout ? aws_kinesis_stream_consumer.lambda[0].arn : null
}
