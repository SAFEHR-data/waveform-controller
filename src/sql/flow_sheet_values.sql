--get the flow sheet values for the particular visit on a particular day
--  the flow sheet numbers are recorded as id_in_application in the visit_observation_type table
--  Temperature       6
--  Noradrenalin      3040102622
--  Metaraminol       12946

SELECT
    vo.observation_datetime AS DateTimeRecorded,

    (array_agg(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '6'
    ))[1] AS "Temperature",

    (array_agg(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '3040102622'
    ))[1] AS "Noradrenaline",

    (array_agg(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '12946'
    ))[1] AS "Metaraminol",
 
    vo.unit AS Units,
    vo.comment AS Comments
    
FROM star.visit_observation AS vo

LEFT JOIN star.visit_observation_type AS vt
    ON vo.visit_observation_type_id = vt.visit_observation_type_id

WHERE vt.id_in_application IN ('6', '3040102622', '12946')
AND vo.valid_from BETWEEN %(start_datetime)s AND %(end_datetime)s
AND vo.hospital_visit_id = %(hospital_visit_id)s

GROUP BY DateTimeRecorded, Units, vo.comment
