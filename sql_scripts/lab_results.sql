-- This selects the values are units of lab tests
-- 1011      CRP
-- 722790196 CRP
-- 390793054 WCC
-- 390793057 WCC
-- 390793060 WCC

select
r.result_last_modified_datetime as date,
(select name from star.lab_test_definition as ltd
where ltd.lab_test_definition_id = r.lab_test_definition_id) as name,
r.value_as_real as value,
r.units,
r.abnormal_flag,
r.comment


from star.lab_result as r
join star.lab_order as o
on r.lab_order_id = o.lab_order_id
where o.hospital_visit_id = 'xx'
and r.result_status  like 'FINAL'
and r.lab_test_definition_id in ('1001', '390793054', '390793057', '390793060', '722790196')
