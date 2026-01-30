# Notes on deployment into production

# How to upgrade Waveform (and/or Emap)

## Background
The current situation is that we are running an instance 
of Emap on star_dev that is independent of the "live" versions
on star_a and star_b, because the waveform export pipeline
is dependent on software changes to Emap, and we don't have time
to deploy those changes into Emap main on our schedule
(rebuilding the database takes ~12 weeks now).


## How to rebuild the system

It depends on what you have changed! You could take the
sledgehammer approach which is rather similar to
[the initial setup in the main README](../README.md):
* Emap: `emap docker down --volumes` to take down the containers and delete the rabbitmq data
* Delete all Emap tables in star_dev as per Emap deployment instructions.
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
> Refer to the Emap deployment guide

If you have made changes to the way we receive waveform HL7
messages, you should stop this container with `emap docker stop waveform-reader`.

This can take a while, because it will try to flush out any HL7
data in memory to disk.

This will stop listening on port 7777, and in the absence of buffering
on the Smartlinx server, we are now losing waveform data forever, so
try to minimise the amount of time it's in this state.
See https://github.com/SAFEHR-data/emap/issues/135 re buffering.

Bring in the latest code with eg. `(cd emap && git pull)`.

Build the new version of the waveform-reader image with
`emap docker build waveform-reader`.

Does any config need updating? See if any config params
have been added/removed
from the Emap global config, and re-run `emap setup -g` as appropriate.

### Drain the rabbitmq queues
Observe the `waveform_emap` and `waveform_export` queues in rabbitmq.
They are consumed by Emap core and waveform-controller respectively.

We disabled incoming messages in the previous step, but the queues
probably still contain messages that were generated with the old version of
waveform-reader, so we must decide what to do with them.

One option is to wait for those consumers to finish their jobs and empty the queues.

If for some reason the consumers are not running or are malfunctioning (perhaps
they are rejecting and requeueing the messages?), then another option is to purge one
or both queues in the rabbitmq admin console.

If the rabbitmq topology has changed, you might consider bringing down the entire
rabbitmq container and deleting its data volume.


### Emap DB and core processor
It's less likely, but you may have changed the Emap core processor or the
Emap star database.

### Waveform controller/exporter (ie. this repo)

Do you need to delete any of the waveform-export files?

Snakemake won't regenerate files if the timestamps of upstream
files suggest they don't need updating. Therefore, if you have made
a change that would affect the contents of those files and wish to
force a re-processing, you will need to manually delete those files.

To force a re-upload only, delete files in `ftps-logs`.

To force a reconversion from CSV to parquet (which includes pseudonymisation),
delete files in pseudonymised.


Files in `original-csv` are a special case as they're input to the snakemake
pipeline, produced by the waveform-controller. If you need to regenerate those,
you will need to replay HL7 messages (see later section).

### Bring it all back up
Generally you should bring things back up in reverse order:

Bring up the waveform-reader (if you ever brought it down).
Emap: `emap docker up -d waveform-reader`

Bring up the waveform controller/export if you ever brought them down.
Waveform: `docker compose up -d`

### Replay old HL7 data


