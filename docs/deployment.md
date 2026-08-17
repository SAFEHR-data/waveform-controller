# Notes on deployment into production

# About

This document is intended for deployers of the Waveform export pipeline,
who likely overlap with its developers.

It describes how to deploy the system into production, and especially how to
"upgrade", ie. re-deploy in an environment where some processing has already taken place.

Because this project required changes to Emap (mainly the waveform-reader),
it also covers when that might need to be upgraded.

## Background
The current situation is that we are running an instance 
of Emap on `star_dev` that is independent of the "live" versions
on `star_a` and `star_b`, because the waveform export pipeline
is dependent on software changes to Emap and we don't have time
to deploy those changes into Emap main on our schedule —
rebuilding the database takes ~12 weeks now.

Although the waveform controller queries `star_[ab]`, not `star_dev`, we still keep
a full Emap system running on `star_dev` so that the streamlit visualisation
can run.

This document should be read in conjunction with the
[pipeline diagram](https://github.com/SAFEHR-data/emap/blob/develop/docs/technical_overview/waveforms/pipeline.md)

## How to rebuild the system

It depends on what you have changed! You could take the
sledgehammer approach which is rather similar to
[the initial setup in the main README](../README.md):
* Emap: `emap docker down --volumes` to take down the containers and delete the rabbitmq data
* Delete all Emap tables in `star_dev` as per Emap deployment instructions.
* Waveform: `docker compose down` to bring everything down
* git pull and rebuild containers for the two repos.
* Change config if necessary
* Bring it all up again

This is mostly going to be unnecessary though, because eg. the
Emap ADT processing is unlikely to have changed.

Let's go for a more granular approach. Each step is potentially
optional, so read carefully.

### Stop the Emap waveform-reader
> ![TIP]
> Refer to the Emap deployment guide at
> https://github.com/SAFEHR-data/emap/blob/main/docs/SOP/release_procedure.md

If you have made changes to the way we receive waveform HL7
messages, you should stop this container with `emap docker stop waveform-reader`.

This can take a while, because it will flush out any HL7
data in memory to disk.

This will stop listening on port 7777, and in the absence of buffering
on the Smartlinx server, we are now losing waveform data forever, so
try to minimise the amount of time it's in this state.
See https://github.com/SAFEHR-data/emap/issues/135 re buffering.

Checkout the code you wish to deploy with eg. `(cd emap && git pull)`.

Build the new version of the waveform-reader image with
`emap docker build waveform-reader`.

Does any config need updating? See if any config params
have been added/removed
from the Emap global config, and re-run `emap setup -g` as appropriate.

### Drain the rabbitmq queues
Observe the `waveform_emap` and `waveform_export` queues in rabbitmq.
They are consumed by Emap core and waveform-controller respectively.

We stopped incoming messages in the previous step, but the queues
probably still contain messages that were generated with the old version of
waveform-reader, so we must decide what to do with them.

One option is to wait for those consumers to finish their jobs and empty the queues.

If for some reason the consumers are not running or are malfunctioning (perhaps
they are rejecting and requeueing the messages), then another option is to purge one
or both queues in the rabbitmq admin console.

If the rabbitmq topology has changed, you might consider bringing down the entire
rabbitmq container and deleting its data volume.


### Emap DB and core processor
Less likely, you may have changed the Emap core processor or the
Emap star database.

If so, you will want to stop and rebuild the `core` service:
```
emap docker stop core
emap docker build core
```
(we will bring it back up later)

We don't have a framework for doing migrations when the database schema has changed, so
any migrations would have to be done on an ad hoc basis.
That's why we tend to delete the entire database and rebuild it.

However, because no other tables depend on the `waveform` table
(ie. it is a "leaf" of the database schema),
it would be relatively easy to delete only that table and let hibernate rebuild it,
thus avoiding a full rebuild.
When the core service comes back up, it would continue to update the non-waveform data.

### Waveform controller/exporter (ie. this repo)

You may need to delete files in the host directory `waveform-export`, which
is bind mounted by the `waveform-controller` and `waveform-exporter` containers.

Snakemake won't regenerate files if the timestamps of upstream
files suggest they don't need updating. Therefore, if you have made
a change that would affect the contents of those files and wish to
force a re-processing, you will need to manually delete those files.

To force a re-upload only, delete files in `ftps-logs`.

To force a reconversion from CSV to parquet (which includes pseudonymisation),
delete files in `pseudonymised` and `hash-lookups`.

Files in `original-csv` are produced by the waveform-controller.
If you need to regenerate those,
you will need to replay HL7 messages (see later section).

### Bring it all back up
It shouldn't matter what order things are brought back up in, so let's do it in the same order
it was brought down.

Bring up any Emap services that we brought down:
Emap repo: `emap docker up -d`

Bring up the waveform controller/export if you brought them down.
Waveform repo: `docker compose up -d`

### Replay old HL7 data

Make sure you have built the image (it's the same image as waveform-reader):
`emap docker build waveform-reader-hl7-replay`

To run:
```
emap docker run waveform-reader-hl7-replay --start-datetime '2024-08-25T00:00:00Z' --end-datetime '2024-08-26T00:00:00Z' --source-location 'UCHT03ICURM06' --dry-run
```

Note: timestamps must be parseable by Java's Instant.parse(). Ie. in ISO long form, with hours, minutes, seconds, and UTC indicator 'Z', as shown above.

Date intervals are half-open (inclusive on the start, exclusive on the end)

`--source-location` is optional; examples values: "UCHT03ICUBED19", "UCHT03ICURM08"; all locations included if not specified.

Filtering by variable is not currently possible.

# Run de-id on ad adhoc basis

> [!NOTE]
> Due to the way scheduled-script.sh pulls in its config from the config file, the contents of
> that file will override any env vars you specify on the command line below.

You need to temporarily change the exporter.env config file to run this command.

You are likely to want to set the following values (example date shown):
```
ONLY_USE_CSV_FROM_YESTERDAY=FALSE
# something shorter than the standard 180 may be needed if you only just processed the data
CSV_AGE_THRESHOLD_MINUTES=???
# use actual date you want to process
PROCESS_CSV_FROM_DATE=1234-12-12
```
docker compose run --entrypoint /app/exporter-scripts/scheduled-script.sh waveform-exporter
```

Remember to put the config back afterwards.
