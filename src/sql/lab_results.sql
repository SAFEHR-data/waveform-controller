-- This selects the values of lab tests
-- 1011      C REACTIVE PROTEIN
-- 686       WHITE CELL COUNT 

SELECT
    r.result_last_modified_datetime AS "DateTimeRecorded",

    MAX(r.value_as_real) FILTER
    (WHERE r.lab_test_definition_id = '1001') AS "CRP",

    MAX(r.value_as_real) FILTER
    (WHERE r.lab_test_definition_id = '686') AS "WCC",

    r.units AS "Units"

FROM {schema_name}.lab_result AS r
LEFT JOIN {schema_name}.lab_order AS o
    ON r.lab_order_id = o.lab_order_id

WHERE 
    r.result_status LIKE 'FINAL'
    AND r.lab_test_definition_id IN ('1001', '686')
    AND r.result_last_modified_datetime >= %(start_datetime)s
    AND r.result_last_modified_datetime < %(end_datetime)s
    AND o.hospital_visit_id = %(hospital_visit_id)s

GROUP BY "DateTimeRecorded", "Units"
