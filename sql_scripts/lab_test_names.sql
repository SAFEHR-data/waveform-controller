select lab_test_definition_id as id,
       name,
       standardised_vocabulary as vocab
from star.lab_test_definition as ltd
where ltd.lab_test_definition_id in ('1001', '390793054', '390793057', '390793060', '722790196')

id	name	vocab
1001	C-reactive protein	
390793054	CSF WCC TUBE 1	
390793057	CSF WCC TUBE 2	
390793060	CSF WCC TUBE 3	
722790196	C-reactive protein	

PaCO2 39947 - in star
PaO2 40191