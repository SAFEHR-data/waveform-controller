# Notes on putting together the EHR needed

## Private scripts

This is a public repository and so we cannot include any scripts that are proprietary from the hospital system EPIC.
These are included in a separate private repository named waveform-private-queries. This has a directory structure

[top-level]/src/sql

so that it can be copied directly onto the directory structure of this repository and thus all scripts will be contained in the same place upon deployment.



## Goal

The ultimate aim is to have one csv per patient per day which looks roughly like

 | DateTimeRecorded | Temperature | noradrenaline | etc  | Secretions | etc | Placementinstant | RemovalInstant | TubeSize | etc |Units | Comments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 08/08/2026 00:00:15 | 36.4 |  |  |  |  | | | | | |
| 08/08/2026 00:00:16 |  | 1 | | | | | | | | mg/L |  |
| 08/08/2026 00:00:17 |  |  |  | None |  | | | | | |
| 08/08/2026 00:02:18 |  |  |  |  |  | 07/08/2026 | |8mm | | |
| 08/08/2026 00:00:15 | 38.5 |  |  |  |  | | | | | | Doctors alerted |

*Note: The insertion date for a tube may well be earlier than the day on which it is recorded as these seem to get populated during the nightly update to caboodle.*

## Current scripts

| script | arguments | record | location of script in repo | database | 
|- | --- | --- |- | --- |
| mrn_based_on_bed_and_datetime.sql | location string | csn |waveform-controller/src/sql | star |
| get_hospital_visit_id.sql| csn | hospital_visit_id | waveform-controller/src/sql| star |
| flow_sheet_values.sql| hospital_visit_id/today/yesterday | part of table above | waveform-controller/src/sql| star |
| lab_results.sql | csn/today/yesterday | part of the table above | waveform-controller/src/sql | star |
| sputum_secretions.sql | csn/today/yesterday | part of the table above | waveform-private-queries/src/sql | caboodle |
| reposition.sql | csn/today/yesterday | part of the table above | waveform-private-queries/src/sql | caboodle |
---

## Unfinished scripts

| script | arguments | record | location of script in repo | database | 
|- | --- | --- |- | --- |
| airway.sql | csn/today/yesterday | part of the table above | waveform-private-queries/src/sql | caboodle |
---
