#!/bin/bash
# Quick pre-deployment checks

echo "🚀 Pre-deployment checks..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run database tests
echo "🔍 Testing database connectivity..."
python test_db.py

if [ $? -eq 0 ]; then
    echo "✅ All checks passed! Safe to deploy."
    exit 0
else
    echo "❌ Tests failed. Do not deploy!"
    exit 1
fi
