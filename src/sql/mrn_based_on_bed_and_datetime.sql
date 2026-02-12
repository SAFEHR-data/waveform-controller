/* Find a medical record number (MRN), NHS number, and contact serial number (CSN) based on location
string and date time. Returns a list of MRN, NHS numbers, and CSN with the
first entry being the most recent.
*/
SELECT
  mn.mrn as mrn,
  mn.nhs_number as nhs_number,
  hv.encounter as csn,
  mn.research_opt_out as research_opt_out
FROM {schema_name}.mrn mn
INNER JOIN {schema_name}.hospital_visit hv
  ON mn.mrn_id = hv.mrn_id
INNER JOIN {schema_name}.location_visit lv
  ON hv.hospital_visit_id = lv.hospital_visit_id
INNER JOIN {schema_name}.location loc
  ON lv.location_id = loc.location_id
WHERE loc.location_string = %(location_string)s
  AND lv.admission_datetime <= %(observation_datetime)s
  -- location visits can abut, so can't use inclusive intervals at both ends
  AND ( lv.discharge_datetime > %(observation_datetime)s OR lv.discharge_datetime IS NULL )
