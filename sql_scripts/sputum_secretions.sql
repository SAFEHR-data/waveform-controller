<- Retrieved the information about sputum and secretions >

SELECT
fv.TakenInstant AS 'DateTimeRecorded',
CASE 
WHEN fsd.FlowsheetRowEpicId = '451120' 
THEN fv.Value 
END 
AS 'Secretions'  ,
CASE 
WHEN fsd.FlowsheetRowEpicId = '302600' 
THEN fv.Value 
END 
AS 'Sputum'  ,
fv.Comment AS Comments

FROM FilteredAccess.FlowsheetValueFact fv 
INNER JOIN FilteredAccess.FlowsheetRowDim fsd ON fv.FlowsheetRowKey = fsd.FlowsheetRowKey
INNER JOIN FilteredAccess.EncounterFact enc ON fv.EncounterKey = enc.EncounterKey

WHERE
(fsd.FlowsheetRowEpicId = '451120' OR 
fsd.FlowsheetRowEpicId ='302600')
AND fv.TakenInstant BETWEEN %(yesterday)s AND %(today)s
AND enc.EncounterEpicCsn = %(csn)
