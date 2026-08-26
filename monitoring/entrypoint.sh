#!/bin/bash

set -eo pipefail

if [ -z "$MONITORING_CRON_SCHEDULE" ]; then
  echo "You must set MONITORING_CRON_SCHEDULE when running this container"
  exit 1
fi

cat > /etc/crontab <<EOF
$MONITORING_CRON_SCHEDULE python /app/monitor.py
EOF

exec supercronic /etc/crontab
