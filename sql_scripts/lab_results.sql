-- This selects the values of lab tests
-- 1011      CRP
-- 722790196 CRP
-- 390793054 WCC
-- 390793057 WCC
-- 390793060 WCC

SELECT
    r.result_last_modified_datetime AS DateTimeRecorded,

    MAX(r.value_as_real) FILTER (WHERE r.lab_test_definition_id = '1001') AS "C-reactive protein",
    MAX(r.value_as_real) FILTER (WHERE r.lab_test_definition_id = '390793054') AS "CSF WCC TUBE 1",
    MAX(r.value_as_real) FILTER (WHERE r.lab_test_definition_id = '390793057') AS "CSF WCC TUBE 2",
    MAX(r.value_as_real) FILTER (WHERE r.lab_test_definition_id = '390793060') AS "CSF WCC TUBE 3",
    MAX(r.value_as_real) FILTER (WHERE r.lab_test_definition_id = '722790196') AS "C-reactive protein"

    r.units AS Units,
    r.abnormal_flag AS Abnormal_result,
    r.comment AS Comments

FROM star.lab_result AS r
LEFT JOIN star.lab_order AS o
    ON r.lab_order_id = o.lab_order_id

WHERE r.result_status  like 'FINAL'
AND 
r.lab_test_definition_id IN ('1001', 
                             '390793054', 
                             '390793057', 
                             '390793060', 
                             '722790196')
AND vo.valid_from BETWEEN %(yesterday)s AND %(today)s
AND o.hospital_visit_id = %(hospital_visit_id)s

GROUP BY DateTimeRecorded, Units, Abnormal_result, Comments
