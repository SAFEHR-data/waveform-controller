# Logging

Logs appear in several locations:
## docker logs
### waveform-exporter container
```docker compose logs -t waveform-exporter```
This shows only the output from the script run by `cron`.

### waveform-controller container

## snakemake logs
Produced by `waveform-exporter`
- waveform-export/snakemake-logs/snakemake-outer-log20260122T173201.log
- ../waveform-export/snakemake-logs/2025-06-04.acbc4701.52912.mL.log
- ../waveform-export/ftps-logs/2025-06-04.8bea0824.52912.mL.ftps.log