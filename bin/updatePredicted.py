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
import mgiutils

db.setTrace()

relevanceFile = ''
relevanceFileName = ''
relevanceTable = 'BIB_Workflow_Relevance'
relevanceKey = 0
userKey = 1001

bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
relevanceVersion = os.getenv('RELEVANCEVERSION')
relevanceFileName = outputDir + '/' + relevanceTable + '.bcp'
relevanceFile = open(relevanceFileName, 'w')

results = db.sql(''' select nextval('bib_workflow_relevance_seq') as maxKey ''', 'auto')
relevanceKey = results[0]['maxKey']

allIsCurrentSQL = ''
setIsCurrentSQL = '''update bib_workflow_relevance set isCurrent = 0 where isCurrent = 1 and _refs_key = %s';\n'''

bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
bcpII = '"|" "\\n" mgd'

loaddate = loadlib.loaddate

fp = open(os.getenv('PREDICTED_RELEVANCE'), 'r')
lineNum = 0
for line in inFile.readlines():

        if lineNum == 0:
                continue

        tokens = line[:-1].split('|')

        mgiID = tokens[0]
        term = tokens[1]
        confidence = tokens[2]

        #this term is not stored in the database
        #absvalue = tokens[3]

        try:
                refKey = db.sql('''select _refs_key from BIB_Citation_Cache where mgiid = '%s' '''% (mgiID), 'auto')[0]
                termKey = db.sql('''select _term_key from voc_term where _vocab_key = 149 and term = '%s' % (term) ''', 'auto')[0]

                relevanceFile.write('%s|%s|%s|1|%s|%s|%s|%s|%s|%s\n' \
                        %(relevanceKey, refKey, termKey, confidence, relevanceVersion, userKey, userKey, loaddate, loaddate))

                relevanceKey += 1

                # set the existing isCurrent = 0
                allIsCurrentSQL += setIsCurrentSQL % (refKey)

        except:
                print('Invalid MGI ID: %s' % (mgiID))
                continue

fp.close()
relevanceFile.flush()
relevanceFile.close()

try:
        # update existing relevance isCurrent = 0
        # make sure this is done *before* the new rows are added
        print(allIsCurrentSQL)
        #db.sql(allIsCurrentSQL, None)
        #db.commit()

        # enter new relevance
        bcpCmd = '%s %s "/" %s %s' % (bcpI, relevanceTable, relevanceFileName, bcpII)
        print(bcpCmd)
        #os.system(bcpCmd)

        # update bib_workflow_relevance serialization
        #db.sql(''' select setval('bib_workflow_relevance_seq', (select max(_Assoc_key) from BIB_Workflow_Relevance)) ''', None)
        #db.commit()

except:
        print('bcp failed: os.system(%s)\n' (bcpCmd))
        

