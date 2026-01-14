#!/bin/bash

# Infrastructure Setup Script
# Initializes and applies Terraform configuration

set -e

TERRAFORM_DIR="terraform/environments/production"

echo "🏗️  Setting up Zappix Demo Infrastructure"
echo "========================================="

# Check for required tools
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform is required but not installed."; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI is required but not installed."; exit 1; }

# Check AWS credentials
echo "🔐 Verifying AWS credentials..."
aws sts get-caller-identity > /dev/null || { echo "❌ AWS credentials not configured."; exit 1; }

# Navigate to Terraform directory
cd "$TERRAFORM_DIR"

# Check for terraform.tfvars
if [ ! -f "terraform.tfvars" ]; then
    echo "⚠️  terraform.tfvars not found!"
    echo "   Please copy terraform.tfvars.example to terraform.tfvars and configure it."
    echo "   cp terraform.tfvars.example terraform.tfvars"
    exit 1
fi

# Initialize Terraform
echo "📦 Initializing Terraform..."
terraform init

# Plan
echo "📋 Planning infrastructure changes..."
terraform plan -out=tfplan

# Ask for confirmation
read -p "Apply these changes? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Aborted"
    exit 1
fi

# Apply
echo "🚀 Applying infrastructure..."
terraform apply tfplan

# Output results
echo ""
echo "✅ Infrastructure setup complete!"
echo ""
terraform output

