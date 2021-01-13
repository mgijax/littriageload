#
#  Purpose:
#
#  secondary triage : Tumor Criteria
#
#       http://mgiprodwiki/mediawiki/index.php/sw:Secondary_Triage_Loader_Requirements#Tumor_Criteria
#       References: relevance status = "keep", Tumorstatus = "New"
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
userKey = 1618

bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
outputDir = os.getenv('OUTPUTDIR')
logDir = os.getenv('LOGDIR')
statusFileName = outputDir + '/' + statusTable + '.Tumor.bcp'
statusFile = open(statusFileName, 'w')
logFileName = logDir + '/secondary.Tumor.log'
logFile = open(logFileName, 'w')
outputFileName = outputDir + '/Tumor.txt'
outputFile = open(outputFileName, 'w')

statusLookup = {}
outputLookup = {}

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

excludedTerms = []
results = db.sql('select term from voc_term where _vocab_key = 164 order by term', 'auto')
for r in results:
    excludedTerms.append(r['term'])
print(excludedTerms)

searchTerms = [
'tumo',
'inoma',
'adenoma',
'sarcoma',
'lymphoma',
'neoplas',
'gioma',
'papilloma',
'leukemia',
'leukaemia',
'ocytoma',
'thelioma',
'blastoma',
'hepatoma',
'melanoma',
'lipoma',
'myoma',
'acanthoma',
'fibroma',
'teratoma',
'glioma',
'thymoma'
]

sql = '''
(
select c._refs_key, c.mgiid, c.pubmedid, s._group_key, v.confidence, lower(d.extractedText) as extractedText
from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s, bib_workflow_data d
where r._refs_key = c._refs_key
and r._refs_key = v._refs_key
and v.isCurrent = 1
and v._relevance_key = 70594667
and r._refs_key = s._refs_key
and s._status_key = 71027551
and s._group_key = 31576667
and r._refs_key = d._refs_key
and d._extractedtext_key not in (48804491)
and d.extractedText is not null
)
order by mgiid desc
'''

results = db.sql(sql, 'auto')
for r in results:

        refKey = r['_refs_key']
        mgiid = r['mgiid']
        pubmedid = r['pubmedid']
        groupKey = r['_group_key']
        confidence = r['confidence']
        termKey = notroutedKey
        term = 'Not Routed'

        logFile.write('\n')
        allSubText = []
        matchesTerm = 0
        matchesExcludedTerm = 0
        extractedText = r['extractedText']
        extractedText = extractedText.replace('\n', ' ')
        extractedText = extractedText.replace('\r', ' ')

        for s in searchTerms:
            for match in re.finditer(s, extractedText):
                subText = extractedText[match.start()-50:match.end()+50]
                if len(subText) == 0:
                    subText = extractedText[match.start()-50:match.end()+50]

                matchesExcludedTerm = 0
                for e in excludedTerms:
                    for match2 in re.finditer(e, subText):
                        matchesExcludedTerm += 1

                # if subText matches excluded term, don't change to "Routed"
                if matchesExcludedTerm == 0:
                        termKey = routedKey;
                        term = 'Routed'
                        matchesTerm += 1

                logFile.write(s + ' [ ' + subText + '] excluded term = ' + str(matchesExcludedTerm) + '\n')
                allSubText.append(subText)

        if mgiid not in statusLookup:

                logFile.write(mgiid + ' ' + pubmedid + ' ' + str(confidence) + ' ' + term+ ' ' + str(matchesTerm) + '\n')

                statusLookup[mgiid] = []
                statusLookup[mgiid].append('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
                        % (statusKey, refKey, groupKey, termKey, isCurrent, \
                              userKey, userKey, loaddate, loaddate))

                outputLookup[mgiid] = []
                outputLookup[mgiid].append(mgiid + '|' + pubmedid + '|' + str(confidence) + '|' + term + '|' + str(matchesTerm) + '|' + str(matchesExcludedTerm) + '|' + '|'.join(allSubText) + '\n')

                statusKey += 1

                # set the existing isCurrent = 0
                allIsCurrentSQL += setIsCurrentSQL % (refKey)

for r in sorted(statusLookup):
        statusFile.write(statusLookup[r][0])

for r in sorted(outputLookup):
        outputFile.write(outputLookup[r][0])

statusFile.flush()
statusFile.close()
logFile.flush()
logFile.close()
outputFile.flush()
outputFile.close()

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

