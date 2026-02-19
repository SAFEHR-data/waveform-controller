--get the flow sheet values for the particular visit
--  the flow sheet numbers are recorded as id_in_application in the visit_observation_type table
--  Temperature       6
--  Noradrenalin      3040102622
--  Metaraminol       12946
--  Secretion amount  451120
--  Sputum amount     302600


select observation_datetime as datetime,
(select display_name
from star.visit_observation_type as vt
where vt.visit_observation_type_id = vo.visit_observation_type_id ) as observation,
value_as_real,
unit,
value_as_text,
comment,
vo.visit_observation_type_id
from star.visit_observation   as vo
left join star.visit_observation_type as vt
on vo.visit_observation_type_id = vt.visit_observation_type_id
where vt.id_in_application in ('6', '12946', '302600', '451120', '3040102622')
and hospital_visit_id = 'xx'