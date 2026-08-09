# Notes on putting together the EHR needed

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
| get_hospital_visit_id.sql| csn | hospital_visit_id | waveform-controller/sql_scripts| star |
| flow_sheet_values.sql| hospital_visit_id/today/yesterday | part of table above | waveform-controller/sql_scripts| star |
| airway.sql | csn/today/yesterday | part of the table above | waveform-controller/sql_scripts | caboodle |
| sputum_secretions.sql | csn/today/yesterday | part of the table above | waveform-controller/sql_scripts | caboodle |

## Unfinished scripts

lab_results.sql need dealing with in the same way as flow_sheet_values

lab_test_names.sql forms part of the above query but is useful for exploring

We need scripts for any of the items in the a tracker that have not yet been covered.
