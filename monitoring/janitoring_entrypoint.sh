#!/bin/bash

set -eo pipefail

if [ -z "$JANITORING_CRON_SCHEDULE" ]; then
  echo "You must set JANITORING_CRON_SCHEDULE when running this container"
  exit 1
fi

cat > /etc/crontab <<EOF
$JANITORING_CRON_SCHEDULE python /app/janitor.py --dry-run
EOF

exec supercronic /etc/crontab
