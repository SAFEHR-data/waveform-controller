
SELECT
lda._CreationInstant as DateTimeRecorded,
lda.PlacementInstant,
lda.RemovalInstant,
fvf.Value AS TubeSize     

FROM FilteredAccess.LdaFact lda
JOIN FilteredAccess.FlowsheetValueFact fvf ON fvf.LdaKey = lda.LdaKey
JOIN FilteredAccess.FlowsheetRowDim frd ON frd.FlowsheetRowKey = fvf.FlowsheetRowKey
JOIN FilteredAccess.EncounterFact enc ON enc.EncounterKey = lda.InitialEncounterKey

WHERE
fvf.FlowsheetRowEpicId ='1120100079'                      
AND enc.Type != 'Anaesthesia'
AND frd.DisplayName like 'Single Lumen Tube Size'
--and enc.PatientDurableKey = '1782941'

AND lda._CreationInstant BETWEEN  %(yesterday)s AND %(today)s
AND enc.EncounterEpicCsn = %(csn)
