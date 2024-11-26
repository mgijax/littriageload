#
#  Purpose:
#
#  1. find any GXD HT pubmed ids that exist in Lit Triage with no J:
#       this means they came in thru Lit Triage from a user or pdfdownload folder
#  2. add a J: and set GXD HT -> Indexed
#
# This is currently not being executed
#

import sys
import os
import db
import mgi_utils
import loadlib

db.setTrace()

referenceFile = ''
referenceFileName = ''
referenceTable = 'ACC_Accession'
statusKey = 0
statusFile = ''
statusFileName = ''
statusTable = 'BIB_Workflow_Status'
statusKey = 0
relevanceKey = 0
relevanceFile = ''
relevanceFileName = ''
relevanceTable = 'BIB_Workflow_Relevance'
userKey = 1667

statusIndexedKey = 31576673
groupKey = 114000000
keepKey = 70594667
prefixPart = 'J:'
mgiTypeKey = 1
logicalDBKey = 1
isPrivate = 0
isPreferred = 1

bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
outputDir = os.getenv('OUTPUTDIR')
referenceFileName = outputDir + '/' + referenceTable + '.bcp2'
referenceFile = open(referenceFileName, 'w')
statusFileName = outputDir + '/' + statusTable + '.bcp2'
statusFile = open(statusFileName, 'w')
relevanceFileName = outputDir + '/' + relevanceTable + '.bcp2'
relevanceFile = open(relevanceFileName, 'w')

results = db.sql(''' select nextval('bib_workflow_status_seq') as maxKey ''', 'auto')
statusKey = results[0]['maxKey']
results = db.sql(''' select nextval('bib_workflow_relevance_seq') as maxKey ''', 'auto')
relevanceKey = results[0]['maxKey']

results = db.sql('select max(_Accession_key) + 1 as maxKey from ACC_Accession', 'auto')
accKey = results[0]['maxKey']

results = db.sql('select max(maxNumericPart) + 1 as maxKey from ACC_AccessionMax where prefixPart = \'J:\'', 'auto')
jnumKey = results[0]['maxKey']

allIsCurrentSql = ''
isCurrentStatusSql = '''update bib_workflow_status set isCurrent = 0 where isCurrent = 1 and _group_key = %s and _refs_key = %s;\n'''
isCurrentRelevanceSql = '''update bib_workflow_relevance set isCurrent = 0 where isCurrent = 1 and _refs_key = %s;\n'''

bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
bcpII = '"|" "\\n" mgd'
bcpCmd1 = '%s %s "/" %s %s' % (bcpI, referenceTable, referenceFileName, bcpII)
bcpCmd2 = '%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII)
bcpCmd3 = '%s %s "/" %s %s' % (bcpI, relevanceTable, relevanceFileName, bcpII)

loaddate = loadlib.loaddate

results = db.sql('''
select distinct c._refs_key, c.pubmedid
from GXD_HTExperiment e, MGI_Property p, BIB_Citation_Cache c
where e._curationstate_key = 20475421 /* Done */
and e._experiment_key = p._object_key
and p._mgitype_key = 42
and p._propertyterm_key = 20475430
and p.value = c.pubmedid 
and c.jnumid is null
''', 'auto')

# update the max accession ID value for J:
if len(results) > 0:
    db.sql('select * from ACC_setMax (%d, \'J:\')' % (len(results)), None)
    db.commit()

for r in results:
        isCurrent = 1
        refKey = r['_Refs_key']
        statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
                %(statusKey, refKey, groupKey, statusIndexedKey, isCurrent, userKey, userKey, loaddate, loaddate))
        statusKey += 1
        relevanceFile.write('%s|%s|%s|%s|||%s|%s|%s|%s\n' \
                %(relevanceKey, refKey, keepKey, isCurrent, userKey, userKey, loaddate, loaddate))
        relevanceKey += 1

        accID = 'J:' + str(jnumKey)
        numericPart = jnumKey
        logicalDBKey = 1
        referenceFile.write('%s|%s|%s|%s|%s|%d|%d|%s|%s|%s|%s|%s|%s\n' \
                        % (accKey, accID, prefixPart, numericPart, logicalDBKey, refKey, mgiTypeKey, \
                        isPrivate, isPreferred, userKey, userKey, loaddate, loaddate))
        accKey += 1
        jnumKey += 1

        # set the existing isCurrent = 0
        allIsCurrentSql += isCurrentStatusSql % (groupKey, refKey)
        allIsCurrentSql += isCurrentRelevanceSql % (refKey)

referenceFile.flush()
referenceFile.close()
statusFile.flush()
statusFile.close()
relevanceFile.flush()
relevanceFile.close()

if allIsCurrentSql != '':
    # update existing reference isCurrent = 0
    # must be done *before* the new rows are added
    db.sql(allIsCurrentSql, None)
    db.commit()

# enter new reference data
os.system(bcpCmd1)
os.system(bcpCmd2)
os.system(bcpCmd3)

# update bib_workflow_status serialization
db.sql(''' select setval('bib_workflow_status_seq', (select max(_Assoc_key) from BIB_Workflow_Status)) ''', None)
db.sql(''' select setval('bib_workflow_relevance_seq', (select max(_Assoc_key) from BIB_Workflow_Relevance)) ''', None)
db.commit()

