#!/bin/bash
set -e

# Initialize feeds.json in the data volume if it doesn't exist
if [ ! -f /app/data/feeds.json ]; then
    cp /app/rss_feeder/feeds.json /app/data/feeds.json
fi

exec python -m rss_feeder
