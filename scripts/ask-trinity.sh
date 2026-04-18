#!/bin/bash
# Ask Trinity - Query the Vertex AI Search documentation assistant
# Usage: ./scripts/ask-trinity.sh "How do I create an agent?"

set -e

PROJECT_ID="mcp-server-project-455215"
ENGINE_ID="trinity-search"
LOCATION="global"

if [ -z "$1" ]; then
    echo "Usage: $0 \"your question\""
    exit 1
fi

QUERY="$1"
ACCESS_TOKEN=$(gcloud auth print-access-token)

response=$(curl -s -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION/collections/default_collection/engines/$ENGINE_ID/servingConfigs/default_search:answer" \
  -d "{
    \"query\": {
      \"text\": \"$QUERY\"
    },
    \"answerGenerationSpec\": {
      \"modelSpec\": {
        \"modelVersion\": \"gemini-2.0-flash-001/answer_gen/v1\"
      },
      \"promptSpec\": {
        \"preamble\": \"You are a helpful assistant that answers questions about Trinity, an autonomous agent orchestration platform. Be concise and practical. If you don't know the answer based on the provided context, say so.\"
      },
      \"includeCitations\": true
    }
  }")

# Extract and display answer
answer=$(echo "$response" | jq -r '.answer.answerText // "No answer generated"')
state=$(echo "$response" | jq -r '.answerQueryUnderstandingInfo.queryClassificationInfo[0].type // "UNKNOWN"')

echo ""
echo "Question: $QUERY"
echo ""
echo "Answer:"
echo "$answer"
echo ""

# Show sources if available
sources=$(echo "$response" | jq -r '.answer.references[]?.chunkInfo.documentMetadata.title // empty' 2>/dev/null | head -5)
if [ -n "$sources" ]; then
    echo "Sources:"
    echo "$sources" | while read -r src; do echo "  - $src"; done
fi
