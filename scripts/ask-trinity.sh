#!/bin/bash
# Ask Trinity - Query the Trinity documentation assistant
# Usage: ./scripts/ask-trinity.sh "How do I create an agent?"
#
# No authentication required - uses public Cloud Function endpoint

set -e

ENDPOINT="https://us-central1-mcp-server-project-455215.cloudfunctions.net/ask-trinity"

if [ -z "$1" ]; then
    echo "Usage: $0 \"your question\""
    echo ""
    echo "Examples:"
    echo "  $0 \"How do I create an agent?\""
    echo "  $0 \"What credentials do agents need?\""
    echo "  $0 \"How do I troubleshoot a stuck agent?\""
    exit 1
fi

QUERY="$1"

response=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  "$ENDPOINT" \
  -d "{\"question\": \"$QUERY\"}")

answer=$(echo "$response" | jq -r '.answer // .error // "No response"')
state=$(echo "$response" | jq -r '.state // "UNKNOWN"')

echo ""
echo "Question: $QUERY"
echo ""
echo "Answer:"
echo "$answer"
echo ""
