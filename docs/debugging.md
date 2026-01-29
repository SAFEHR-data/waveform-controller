# About
This is a brief guide to inspecting the state of the waveform data pipeline.
Eg, looking for intermediate data or error messages if something
is not coming through as expected.

# Start here

It is helpful to refer to the pipeline diagram at
https://github.com/SAFEHR-data/emap/blob/develop/docs/technical_overview/waveforms/pipeline.md
to get an overview and find the right place to look.

First, let's see what data is present in the `waveform-export` directory.

Are there recent files in `ftps-logs`? 

> [!NOTE]
> The timestamps that are part of the file names are based on when the data is from, not when they were processed by us!

> [!TIP]
> Use `ls -latr` to see the latest files in a directory.

If the relevant `*.uploaded.json` marker file is present, this means the FTPS
upload to the DSH happened without an error.
The file contents are upload stats in JSON format.
Uploads will also generate email notifications from the DSH. 

If the marker file is not present, let's check the
other end of our pipeline: are there recent files in `original-csv`? 
If not then you need to look at the `waveform-controller` logs,
or failing that further upstream, at the Rabbitmq server (see later section).

If files in `original-csv` are present, then the error is somewhere inside our pipeline,
and you should check the logs in `snakemake-logs` (see later section).

Parquets that are a direct translation from the CSV are found in `original-parquet`.

Parquets that have been pseudonymised are found in `pseudonymised`.


# Logging summary

Logs are found in:
* Docker container logs
* Snakemake top-level logs
* Snakemake job-level logs

> [!CAUTION]
> Always be aware that logs may contain sensitive information. The only
> files considered safe for upload to the DSH are those in the `pseudonymised`
> directory.

## Docker logs

### `waveform-controller` container
```docker compose logs -t waveform-controller```
Shows the `waveform-controller` service logs. Useful for:
- Emap connectivity
- RabbitMQ connectivity
- patient correlation query errors (search for "unmatched")
- CSV output failures

This log is not very chatty if everything is going well.

### `waveform-exporter` container
```docker compose logs -t waveform-exporter```
Shows the output from the cron-triggered script `scheduled-script.sh`.
Useful for high-level pipeline failures before Snakemake starts, or
Snakemake startup failures (eg. when snakemake already running)

## Snakemake logs

Written to the mounted volume under `waveform-export/snakemake-logs/`.
These logs describe pipeline orchestration and per-rule execution.

### `snakemake-outer-log*.log`
Top-level Snakemake run logs, including:
- recently written CSVs that were temporarily excluded from processing (search "File too new")
- job summaries and Snakemake DAG resolution
- more detailed errors when Snakemake itself fails

Unlike data files, the timestamps in these file names are when the snakemake
pipeline was invoked.

### `{date}.{hashed_csn}.{variable_id}.{channel_id}.{units}.log`
Job-level log for the `csv_to_parquet` rule. Contains:
- CSV -> parquet info
- pseudonymisation steps

## FTPS logs and marker files

Produced under `waveform-export/ftps-logs/`.

### `{date}.{hashed_csn}.{variable_id}.{channel_id}.{units}.ftps.log`
Job-level FTPS upload logs. Useful for:
- connection/authentication errors
- transfer failures

### `{date}.{hashed_csn}.{variable_id}.{channel_id}.{units}.ftps.uploaded.json`
Upload marker file (aka sentinel) written after a successful transfer.
It contains, in JSON format:
- `uploaded_file` (the uploaded file path)
- `upload_time_secs` (time to upload in seconds using monotonic clock)
- `start_timestamp` and `end_timestamp` (wall clock UTC start and end timestamp)

Example paths:
- `waveform-export/snakemake-logs/snakemake-outer-log20260122T173201.log`
- `waveform-export/snakemake-logs/2025-06-04.acbc4701.52912.mL.log`
- `waveform-export/ftps-logs/2025-06-04.8bea0824.52912.mL.ftps.log`
- `waveform-export/ftps-logs/2025-06-04.8bea0824.52912.mL.ftps.uploaded.json`

# Rabbitmq (part of Emap)

If the `waveform-controller` service appears to be up and running but is
not generating data, you could check the `waveform_export` queue
in the rabbitmq server, which is part of Emap.

If there are no messages present, it's possible that the waveform reader (also 
part of Emap) is not generating them.

# Waveform reader (part of Emap)
This receives HL7 data on a TCP port from the Capsule server.
It writes received messages
to the docker host directory `waveform-saved-messages`, so look
there for recent messages.

Useful commands, to be run from the emap venv (see Emap repo for more details):
* `emap docker ps` check for container up status (`waveform-reader`)
* `emap docker logs waveform-reader` see if HL7 messages are being received, check for errors
