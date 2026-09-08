# File tidy up (waveform-janitoring)

## Suggested retention times

| Data                               | Size | Replaceability | Comment | Suggested deletion policy |
|--------|--------|--------|--------|--------|
| compressed HL7            | Large | Cannot be replaced |  | Never delete unless under duress. If disk gets low, try to find more disk, or delete old stuff first if we have confidence that our uploaded data will not need to be re-processed. Archives are indexed by time and bed, but ALL variables are mixed together, so targeted deletion is only possible by time and bed.  |
| original CSV                    | Large but see #15  | Can be reprocessed from HL7 | can be useful for debugging | Delete after 30 days or if disk gets low; consider targeted deletion (see #79) |
| original parquet               | Small | Can be reprocessed from CSV | parquets are generated in a single step from CSV | Delete after 30 days or if disk gets low; consider targeted deletion (see #79) |
| pseduonymised parquet | Small | Can be reprocessed from CSV | parquets are generated in a single step from CSV | Delete after 30 days or if disk gets low; consider targeted deletion (see #79) |
| pre-upload tar files         | Small | Is an intermediate file for upload | Not needed except for (short term) debugging | Delete after 30 days or if disk gets low; consider deleting immediately after upload | 

Retention times for file types that are only useful for debugging could be shortened when we have more confidence in the pipeline.

## Design decisions

In the first iteration of this feature, retention times are evaluated against
file modification times. Ie. processing time.

It might, in future, be reasonable to also take observation time into account
(ie. using the dirname "2024-10-01" to determine when the data relates to).

For live data, these time stamps will be very similar so it doesn't matter which we use.

But if we reprocess some data from stored HL7 archives,
the modified times could be quite new vs the observation times.
If we only use modification times, a large amount of data could be produced quite quickly
that won't get cleared up, possibly leading to a full disk.
If we only use observation times and the data is sufficiently old, we could see CSV files being
deleted before we have a chance to convert and upload them.
Therefore it seems likely that to solve those problems we'd have to somehow take both into account.

There shouldn't be a scenario where observation times are newer than modification times
(bar synthetic data).

Snakemake has the ability to mark files as temporary. They are immediately deleted after they are needed.
However, we want to keep files for a certain time after snakemake has finished, so we can't use it.


## Configuration of janitoring service

See [janitoring config example file](../config.EXAMPLE/janitoring.env.EXAMPLE) for config variables.

## Recommended procedure for enabling this feature

Since deleting our precious data is inherently a risky process, I would recommend doing
this is in a phased way.

### Config change (observation phase only)
(dry run mode is left on, host still mounts read-only)

1) Set all `*_RETENTION_*` config options (see previous section) on the GAE to the intended values
   (Recommend leaving HL7 deletion option as blank so as not to delete, unless we're really desperate).
1) Set `JANITORING_CRON_SCHEDULE` to something not too aggressive (few times a day?)
1) Re-up the `waveform-janitoring` container.

After it's run, you can look at the container logs to get a list of files
that would have been deleted, to check it looks good and that no irreplaceable data would be deleted accidentally.
You can also see the number of bytes that would be deleted on Grafana.

### Enable the changes for real
Code change will be needed:
1) Remove the `--dry-run` arg from the `janitoring_entrypoint.sh` script
1) Change the container volume mount options for `/waveform-export` and/or `/waveform-saved-messages` from `ro` to `rw`.
1) Re-deploy as normal
