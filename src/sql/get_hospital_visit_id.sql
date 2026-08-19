-- Retrieve the hospital_visit_id associated with the csn value applied to this function --

select hospital_visit_id from %(schema)s.hospital_visit  as hv
where  hv.encounter = %(csn)s  -- note the CSN must be in quotes                      
