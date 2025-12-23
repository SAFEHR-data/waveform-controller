#!/bin/bash

set -euo pipefail

# This script is intended to be run by the cron scheduler
snakemake --snakefile /app/src/pipeline/Snakefile --cores 1 /waveform-exports