/* Find a medical record number (MRN) and NHS number based on location
string and date time. Returns a list of MRN and NHS numbers with the
first entry being the most recent.
*/
SELECT
  mn.mrn as mrn,
  mn.nhs_number as nhs_number
FROM star.mrn mn
INNER JOIN star.hospital_visit hv
  ON mn.mrn_id = hv.mrn_id
INNER JOIN star.location_visit lv
  ON hv.hospital_visit_id = lv.hospital_visit_id
INNER JOIN star.location loc
  ON lv.location_id = loc.location_id
WHERE loc.location_string = %(location_string)s
  AND hv.valid_from BETWEEN %(start_datetime)s AND %(end_datetime)s
ORDER by hv.valid_from DESC
