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

The uploaded file name is stored in JSON on the GAE in the daily uploaded sentinel file:
eg. `waveform-export/ftps-logs/2024-09-12/2024-09-12.uploaded.json`

### Extraction on the DSH side
See
[UCL DSH docs on File Transfer Portal]https://www.ucl.ac.uk/isd/services/file-storage-sharing/data-safe-haven-dsh/data-safe-haven-user-guide-faqs#File%20Transfer%20Portal
for background information.

Uploaded files go into the Q: drive on the DSH and are auto deleted after 30 days, unless moved to the S: drive.

There is [a script to make this transfer on the DSH side](../../scripts/dsh/extract.py).

It must be manually run by a member of the `WAVEFORM` DSH share more often than every 30 days.

#### To run it

First deploy the script onto the DSH. This is manual but very simple. We do everything under `S:\WAVEFORM`
so we can all see what extraction has taken place.

1. Inside this repository, check out the version you wish to deploy.
2. Log into the DSH File Transfer Portal as your own user
3. Upload `scripts/dsh/extract.py` to the portal
4. On the DSH Desktop, in a Git Bash window, run `mv /q/${YOUR_USER_ID}/extract.py /s/WAVEFORM/extract_script/extract.py`

Now you can run the script in a Git Bash Window:
```
cd /s/WAVEFORM/extract_script
python extract.py --help
# eg.
python extract.py --instance-name gae-testing --dry-run
```
When we go into production, instance name can be omitted.

Later TAR uploads can overwrite earlier files when they are extracted.

All output is logged to a directory adjacent to the script.
