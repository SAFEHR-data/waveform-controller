# Recent analysis of storage requirements

Now that we have some real world usage, we can make better estimates of our storage requirements.

During the era in which we had 10 beds incoming, I am basing the estimates on the calendar day
that used the *most* storage. Usage varies dramatically depending
on whether the beds are in use, or if the patient is ventilated, etc, so it's good to assume the worst case.

| Data type                  | Max daily usage, 10 beds enabled (kiB) | Est. 40 beds, 1 day (kiB) | Est. 40 beds, 183 days |
|----------------------------| -------------------------------------- |---------------------------|------------------------|
| HL7 BZ2                    | 399896 (21/9)                          | 1599584                   | **279 GiB**            |
| CSV                        | 2314848 (19/9)                         | 9259392                   | **1616 GiB**           |
| CSV (bzip2 --best)         | (253294)                               | (1013176)                 | **177 GiB**            |
| orig parquet               | 462704 (19/9)                          | 1850816                   | **323 GiB**            |
| pseud parquet              | 462760 (19/9)                          | 1851040                   | **323 GiB**            |
| Total with current methods | 3640208 (3.47GiB)                      | 14560832 (13.9GiB)        | ***2544 GiB***         |
| Total with compressed CSV  | 1578654 (1.51GiB)                      | 6314616 (6.02GiB)         | ***1102 GiB***         |


The compressed CSV option would require the implementation of
https://github.com/SAFEHR-data/waveform-controller/issues/15#issuecomment-5916464129

This doesn't include any headroom for (eg) reprocessing existing HL7 data before deleting the old outputs,
or other usage of GAE01.