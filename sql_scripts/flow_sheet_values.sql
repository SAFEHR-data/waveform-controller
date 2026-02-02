select observation_datetime as datetime,
value_as_real,
unit,
value_as_text,
comment,
vo.visit_observation_type_id ,
(select display_name
from star.visit_observation_type as vt
where vt.visit_observation_type_id = vo.visit_observation_type_id ) as observation
from star.visit_observation   as vo
left join star.visit_observation_type as vt
on vo.visit_observation_type_id = vt.visit_observation_type_id
where hospital_visit_id = 'csn'