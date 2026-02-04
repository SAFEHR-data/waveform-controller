select
result_last_modified_datetime as date,
value_as_real as value,
units,
abnormal_flag,
comment


from star.lab_result as r
join star.lab_order as o
on r.lab_order_id = o.lab_order_id
where o.hospital_visit_id = 'xxx'
and r.result_status  like 'FINAL'
and r.lab_test_definition_id in ('1001', '390793054', '390793057', '390793060', '722790196')
