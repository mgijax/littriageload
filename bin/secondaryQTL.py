#
#  Purpose:
#
#  secondary triage : QTL Criteria
#
#       http://mgiprodwiki/mediawiki/index.php/sw:Secondary_Triage_Loader_Requirements#QTL_Criteria
#       References: relevance status = "keep", QTLstatus = "New"
#       text to search: extracted text except reference section
#       text to look for: (case insensitive)
#

import sys
import os
import re
import db
import mgi_utils
import loadlib

db.setTrace()

statusFile = ''
statusFileName = ''
statusTable = 'BIB_Workflow_Status'
statusKey = 0
userKey = 1001

bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
outputDir = os.getenv('OUTPUTDIR')
logDir = os.getenv('LOGDIR')
statusFileName = outputDir + '/' + statusTable + '.QTL.bcp'
statusFile = open(statusFileName, 'w')
logFileName = logDir + '/littriageload.secondary.QTL.log'
logFile = open(logFileName, 'w')
outFileName = outputDir + '/QTL.txt'
outFile = open(outFileName, 'w')

results = db.sql(''' select nextval('bib_workflow_status_seq') as maxKey ''', 'auto')
statusKey = results[0]['maxKey']

allIsCurrentSQL = ''
setIsCurrentSQL = '''update bib_workflow_status set isCurrent = 0 where isCurrent = 1 and _refs_key = %s;\n'''

bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
bcpII = '"|" "\\n" mgd'
bcpCmd = '%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII)

loaddate = loadlib.loaddate

isCurrent = "1"
routedKey = "31576670"
notroutedKey = "31576669"

searchTerms = [
'qtl'
]

sql = '''
select c._refs_key, c.mgiid, c.pubmedid, s._group_key, lower(d.extractedText) as extractedText
from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s, bib_workflow_data d
where r._refs_key = c._refs_key
and r._refs_key = v._refs_key
and v.isCurrent = 1
and v._relevance_key = 70594667
and r._refs_key = s._refs_key
and s._status_key = 71027551
and s._group_key = 31576668
and r._refs_key = d._refs_key
and d._extractedtext_key not in (48804491)
and d.extractedText is not null
order by mgiid desc
'''

results = db.sql(sql, 'auto')
for r in results:

        logFile.write('\n')
        refKey = r['_refs_key']
        mgiid = r['mgiid']
        pubmedid = r['pubmedid']
        groupKey = r['_group_key']
        termKey = notroutedKey
        term = 'Not Routed'

        allSubText = []
        matchesTerm = 0
        extractedText = r['extractedText']
        extractedText = extractedText.replace('\n', ' ')
        extractedText = extractedText.replace('\r', ' ')
        for s in searchTerms:
            for match in re.finditer(s, extractedText):
                subText = extractedText[match.start()-50:match.end()+50]
                if len(subText) == 0:
                    subText = extractedText[match.start()-10:match.end()+10]
                termKey = routedKey;
                term = 'Routed'
                logFile.write(s + ' [' +  subText + ']\n')
                allSubText.append(subText)
                matchesTerm += 1

        logFile.write(mgiid + ' ' + pubmedid + ' ' + term + ' ' + str(matchesTerm) + '\n')

        statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
                % (statusKey, refKey, groupKey, termKey, isCurrent, \
                              userKey, userKey, loaddate, loaddate))

        outFile.write(mgiid + '|' + pubmedid + '|' + term + '|' + str(matchesTerm) + '|' + '|'.join(allSubText) + '\n')

        statusKey += 1

        # set the existing isCurrent = 0
        allIsCurrentSQL += setIsCurrentSQL % (refKey)

statusFile.flush()
statusFile.close()
logFile.flush()
logFile.close()
outFile.flush()
outFile.close()

# update existing relevance isCurrent = 0
# must be done *before* the new rows are added
#print(allIsCurrentSQL)
#db.sql(allIsCurrentSQL, None)
#db.commit()

# enter new relevance data
#os.system(bcpCmd)

# update bib_workflow_status serialization
#db.sql(''' select setval('bib_workflow_status_seq', (select max(_Assoc_key) from BIB_Workflow_Status)) ''', None)
#db.commit()

