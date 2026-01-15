provider "aws" {
  region = var.aws_region
}

# VPC Configuration
resource "aws_vpc" "proctoring_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "proctoring-vpc"
  }
}

# Subnets
resource "aws_subnet" "public_subnet_1" {
  vpc_id                  = aws_vpc.proctoring_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "proctoring-public-subnet-1"
  }
}

resource "aws_subnet" "public_subnet_2" {
  vpc_id                  = aws_vpc.proctoring_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true

  tags = {
    Name = "proctoring-public-subnet-2"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "proctoring_igw" {
  vpc_id = aws_vpc.proctoring_vpc.id

  tags = {
    Name = "proctoring-igw"
  }
}

# Route Table
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.proctoring_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.proctoring_igw.id
  }

  tags = {
    Name = "proctoring-public-rt"
  }
}

# S3 Bucket for Recordings
resource "aws_s3_bucket" "proctoring_recordings" {
  bucket = "proctoring-recordings-${var.environment}"

  tags = {
    Name = "Proctoring Recordings"
  }
}

resource "aws_s3_bucket_versioning" "proctoring_recordings_versioning" {
  bucket = aws_s3_bucket.proctoring_recordings.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "proctoring_lifecycle" {
  bucket = aws_s3_bucket.proctoring_recordings.id

  rule {
    id     = "archive-old-recordings"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "proctoring_db" {
  identifier             = "proctoring-db-${var.environment}"
  engine                 = "postgres"
  engine_version         = "14.7"
  instance_class         = "db.r5.xlarge"
  allocated_storage      = 100
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = "proctoringdb"
  username               = var.db_username
  password               = var.db_password
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.proctoring_db_subnet.name
  multi_az               = true
  backup_retention_period = 7
  skip_final_snapshot    = false
  final_snapshot_identifier = "proctoring-db-final-snapshot"

  tags = {
    Name = "proctoring-database"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "proctoring_redis" {
  cluster_id           = "proctoring-redis-${var.environment}"
  engine               = "redis"
  node_type            = "cache.r5.large"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.0"
  port                 = 6379
  security_group_ids   = [aws_security_group.redis_sg.id]
  subnet_group_name    = aws_elasticache_subnet_group.proctoring_redis_subnet.name

  tags = {
    Name = "proctoring-redis"
  }
}

# Application Load Balancer
resource "aws_lb" "proctoring_alb" {
  name               = "proctoring-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]

  enable_deletion_protection = false

  tags = {
    Name = "proctoring-alb"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "proctoring_cluster" {
  name = "proctoring-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "proctoring-cluster"
  }
}

# Auto Scaling Group for ECS
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.proctoring_cluster.name}/${aws_ecs_service.proctoring_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu_scaling" {
  name               = "cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "proctoring_logs" {
  name              = "/ecs/proctoring-${var.environment}"
  retention_in_days = 30

  tags = {
    Name = "proctoring-logs"
  }
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "proctoring_cdn" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Proctoring System CDN"
  default_root_object = "index.html"

  origin {
    domain_name = aws_s3_bucket.proctoring_recordings.bucket_regional_domain_name
    origin_id   = "S3-proctoring-recordings"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.proctoring_oai.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-proctoring-recordings"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "proctoring-cdn"
  }
}

# Output values
output "alb_dns_name" {
  value = aws_lb.proctoring_alb.dns_name
}

output "rds_endpoint" {
  value = aws_db_instance.proctoring_db.endpoint
}

output "s3_bucket_name" {
  value = aws_s3_bucket.proctoring_recordings.id
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.proctoring_cdn.domain_name
}
