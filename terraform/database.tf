resource "aws_security_group" "rds" {
  name        = "nsw-property-rds-sg"
  description = "Allow PostgreSQL access from anywhere"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_db_instance" "property" {
  identifier     = "property-db"
  db_name        = var.db_name
  instance_class = "db.t3.micro"
  engine         = "postgres"
  engine_version = "16"
  username       = var.db_username
  password       = var.db_password

  allocated_storage      = 20
  publicly_accessible    = true
  skip_final_snapshot    = true
  deletion_protection    = true
  vpc_security_group_ids = [aws_security_group.rds.id]

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [password]
  }
}
