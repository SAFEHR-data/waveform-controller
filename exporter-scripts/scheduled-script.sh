#!/bin/bash

set -euo pipefail

# This script is to be run by the cron scheduler, and its
# output goes to the docker logs.
# The snakemake output goes to its own log file as defined here.
# These files will end up on Windows so be careful about disallowed characters in the names.
date_str=$(date --utc +"%Y%m%dT%H%M%S")

# log file for the overall snakemake run (as opposed to per-job logs,
# which are defined in the snakefile)
outer_log_file="/waveform-export/snakemake-logs/snakemake-outer-log${date_str}.log"
# snakemake has not run yet so will not create the log dir; do it manually
mkdir -p "$(dirname "$outer_log_file")"
touch "$outer_log_file"
# bring in envs from file because cron gives us a clean environment
set -a
source /config/exporter.env
set +a
# Now that we have loaded config file, apply default values
SNAKEMAKE_CORES="${SNAKEMAKE_CORES:-1}"
echo "$0: invoking snakemake, cores=$SNAKEMAKE_CORES, logging to $outer_log_file"
# For telling the pipeline not to go all the way
SNAKEMAKE_RULE_UNTIL="${SNAKEMAKE_RULE_UNTIL:-all}"
set +e
snakemake --snakefile /app/src/pipeline/Snakefile \
  --cores "$SNAKEMAKE_CORES" \
  --until "$SNAKEMAKE_RULE_UNTIL" \
  --config CSV_AGE_THRESHOLD_MINUTES="${CSV_AGE_THRESHOLD_MINUTES}" ONLY_USE_CSV_FROM_YESTERDAY="${ONLY_USE_CSV_FROM_YESTERDAY}" \
  >> "$outer_log_file" 2>&1
ret_code=$?
set -e
echo "$0: snakemake exited with return code $ret_code"
exit $ret_code
