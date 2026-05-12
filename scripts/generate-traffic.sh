#!/bin/bash
# Generate realistic traffic for observability demos
# Includes normal requests, errors, and varying patterns

BASE_URL=${1:-http://localhost:30080}
DURATION=${2:-120}   # seconds
echo "Generating traffic to $BASE_URL for ${DURATION}s"
echo "Watch dashboards while this runs!"
echo ""

END=$(($(date +%s) + DURATION))
COUNT=0
CODES=()

while [ $(date +%s) -lt $END ]; do
  COUNT=$((COUNT + 1))

  # Shorten URLs
  RESPONSE=$(curl -s -X POST "$BASE_URL/shorten" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"https://example-$COUNT.com/path?q=$RANDOM\"}" \
    --max-time 5 2>/dev/null)

  CODE=$(echo $RESPONSE | python3 -c \
    "import sys,json
try:
    print(json.load(sys.stdin)['short_code'])
except:
    print('')" 2>/dev/null)

  if [ -n "$CODE" ]; then
    CODES+=($CODE)
    echo "  [$COUNT] Shortened → $CODE"

    # Follow redirect
    curl -s -o /dev/null \
      "$BASE_URL/r/$CODE" \
      --max-time 5 2>/dev/null

    # Get stats
    curl -s -o /dev/null \
      "$BASE_URL/stats/$CODE" \
      --max-time 5 2>/dev/null
  fi

  # Health checks
  curl -s -o /dev/null "$BASE_URL/health" 2>/dev/null

  # Random existing redirect
  if [ ${#CODES[@]} -gt 0 ]; then
    RANDOM_CODE=${CODES[$RANDOM % ${#CODES[@]}]}
    curl -s -o /dev/null \
      "$BASE_URL/r/$RANDOM_CODE" \
      --max-time 5 2>/dev/null
  fi

  # Simulate 404s (invalid codes)
  curl -s -o /dev/null \
    "$BASE_URL/r/invalid" \
    --max-time 5 2>/dev/null

  sleep 1
done

echo ""
echo "✅ Traffic generation complete"
echo "Shortened $COUNT URLs"
