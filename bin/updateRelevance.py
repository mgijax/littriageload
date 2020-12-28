#
#  Purpose:
#
#  1. input:  ${PREDICTED_RELEVANCE}
#
#  2. create bib_workflow_relevance records
#
#  3. set existing bib_workflow_relevance.isCurrent = 0
#

import sys
import os
import db
import mgi_utils
import loadlib

db.setTrace()

relevanceFile = ''
relevanceFileName = ''
relevanceTable = 'BIB_Workflow_Relevance'
relevanceKey = 0
userKey = 1001

bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
relevanceVersion = os.getenv('RELEVANCE_VERSION')
outputDir = os.getenv('OUTPUTDIR')
relevanceFileName = outputDir + '/' + relevanceTable + '.bcp2'
relevanceFile = open(relevanceFileName, 'w')

results = db.sql(''' select nextval('bib_workflow_relevance_seq') as maxKey ''', 'auto')
relevanceKey = results[0]['maxKey']

allIsCurrentSQL = ''
setIsCurrentSQL = '''update bib_workflow_relevance set isCurrent = 0 where isCurrent = 1 and _refs_key = %s;\n'''

bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
bcpII = '"|" "\\n" mgd'
bcpCmd = '%s %s "/" %s %s' % (bcpI, relevanceTable, relevanceFileName, bcpII)

loaddate = loadlib.loaddate

inFile = open(os.getenv('PREDICTED_RELEVANCE'), 'r')
lineNum = 0
for line in inFile.readlines():

        if lineNum == 0:
                lineNum += 1
                continue

        lineNum += 1
        tokens = line[:-1].split('|')

        mgiID = tokens[0]
        term = tokens[1]
        confidence = tokens[2]

        # ignore; this term is not stored in the database
        #absvalue = tokens[3]

        refKey = db.sql('''select _refs_key from BIB_Citation_Cache where mgiid = '%s' '''% (mgiID), 'auto')[0]['_refs_key']
        termKey = loadlib.verifyTerm('', 149, term, lineNum, None)

        relevanceFile.write('%s|%s|%s|1|%s|%s|%s|%s|%s|%s\n' \
                %(relevanceKey, refKey, termKey, confidence, relevanceVersion, userKey, userKey, loaddate, loaddate))

        relevanceKey += 1

        # set the existing isCurrent = 0
        allIsCurrentSQL += setIsCurrentSQL % (refKey)

inFile.close()
relevanceFile.flush()
relevanceFile.close()

# update existing relevance isCurrent = 0
# must be done *before* the new rows are added
db.sql(allIsCurrentSQL, None)
db.commit()

# enter new relevance data
os.system(bcpCmd)

# update bib_workflow_relevance serialization
db.sql(''' select setval('bib_workflow_relevance_seq', (select max(_Assoc_key) from BIB_Workflow_Relevance)) ''', None)
db.commit()

