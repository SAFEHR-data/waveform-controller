select lab_test_definition_id as id,
       name,
       standardised_vocabulary as vocab
from star.lab_test_definition as ltd
where ltd.lab_test_definition_id in ('1001', '390793054', '390793057', '390793060', '722790196')