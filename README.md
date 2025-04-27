# AI News Radio Project

## Setup
1. Start Kafka: `docker-compose up -d`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure feeds in `rss_feeder/feeds.json`

## Running
- Main app: `python -m rss_feeder`
- Health monitor: http://localhost:8000/health

## Monitoring
Check logs in:
- `data/logs/`
- `dql_failed_articles.log`
