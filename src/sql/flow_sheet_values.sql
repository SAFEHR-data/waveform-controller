-- get the flow sheet values for the particular visit on a particular day
--  the flow sheet numbers are recorded as id_in_application
-- in the visit_observation_type table
--  Temperature       6
--  Noradrenaline     3040102622  
--  Metaraminol       12946
--  PaO2              40191
--  PaCO2             39947


SELECT
    vo.observation_datetime AS "FlowsheetDateTimeRecorded",

    MAX(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '6'
    ) AS "FlowsheetTemperature",

    MAX(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '3040102622'
    ) AS "FlowsheetNoradrenaline",

    MAX(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '12946'
    ) AS "FlowsheetMetaraminol",

    MAX(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '40191'
    ) AS "FlowsheetPaO2",

    MAX(vo.value_as_real) FILTER (
        WHERE vt.id_in_application = '39947'
    ) AS "FlowsheetPaCO2",

    vo.unit AS "FlowsheetUnits"

FROM {schema_name}.visit_observation AS vo

LEFT JOIN {schema_name}.visit_observation_type AS vt
    ON vo.visit_observation_type_id = vt.visit_observation_type_id

WHERE
    vt.id_in_application IN ('6', '3040102622', '12946', '40191', '39947')
    AND vo.valid_from >= %(start_datetime)s AND vo.valid_from < %(end_datetime)s
    AND vo.hospital_visit_id = %(hospital_visit_id)s 

GROUP BY "FlowsheetDateTimeRecorded", "FlowsheetUnits"
