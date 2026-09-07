# DSH

Only files from the `pseudonymised` directory are uploaded.
There are safeguards to avoid accidentally uploading from any other directory.

## DSH FTPS

### Write-only uploader accounts

See slab article on
[how to configure the uploader accounts](https://uclh.slab.com/posts/ftps-dsh-uploads-9otokl8x).

### Notifications

One email notification is sent from the DSH per uploaded file.
We need to upload ~hundreds every day, therefore we use a temporary TAR file so that
all our parquets are uploaded in one go.

The TAR file is named according to the *time of upload*, but the file structure within it
is done according to the event times of the data.

Example output of `tar tvf`:
```
-rw-r--r--  0 root   root    10622 24 Aug 17:17 2024-09-12/2024-09-12.4e121edfa3d75b935975bdf2db2c32e229ab3c2764873b506b3fec192bd0b8ec.1570.noCh.cmH2O.parquet
-rw-r--r--  0 root   root    10982 24 Aug 17:17 2024-09-12/2024-09-12.6aae1d263b6029b2344750c9e56a2ccadbd2bf6b08bd0fb6469f4274d96fbb3d.1408.noCh.s.parquet
...
```

Naming by upload time means that subsequently uploaded TAR files
will never overwrite previous ones.
This allows for incremental uploads; that is, the addition of extra data
(eg. new variables, new patients)
for dates that have already had an upload in the past.
*However*, the extracted files will clash in name, as the names
of the parquets within are anchored to the original event date.
It would be the job of a future DSH extractor script to do the right thing here.
Eg. to have a rule that extracts from later uploads always take precedence.
See [issue #84](https://github.com/SAFEHR-data/waveform-controller/issues/84) .

The uploaded file name is stored in JSON on the GAE in the daily uploaded sentinel file:
eg. `waveform-export/ftps-logs/2024-09-12/2024-09-12.uploaded.json`
