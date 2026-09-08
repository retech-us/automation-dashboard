#!/bin/bash
# Quick start script for local development server
# Usage: ./dev-server.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "=================================================="
echo "Automation Dashboard - Development Server"
echo "=================================================="
echo ""
echo "Starting local server on localhost:6060..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "   Please install Python 3 from: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo "✓ Serving files from: $PROJECT_ROOT"
echo ""
echo "Dashboard available at:"
echo "  → http://localhost:6060"
echo "  → http://localhost:6060/index.html"
echo ""
echo "Press CTRL+C to stop server"
echo "=================================================="
echo ""

# Run the server
python3 "$PROJECT_ROOT/server.py"
