#!/bin/bash

# (can't use -u because need to check for potentially unset var)
set -eo pipefail

CRON_OUTPUT_FILE="/var/log/cron_output.log"
touch "$CRON_OUTPUT_FILE"
# Set up cron schedule according to the environment variable
if [ -z "$EXPORTER_CRON_SCHEDULE" ]; then
  echo "You must set EXPORTER_CRON_SCHEDULE when running this container"
  exit 1
fi
set -x
cat <<EOF | crontab -
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/usr/bin/bash
$EXPORTER_CRON_SCHEDULE /app/exporter-scripts/scheduled-script.sh >> "$CRON_OUTPUT_FILE" 2>&1
EOF

# run cron in background, and ensure that output goes to docker logs
cron
tail -f "$CRON_OUTPUT_FILE"
