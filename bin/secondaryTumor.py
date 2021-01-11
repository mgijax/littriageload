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
userKey = 1001

bcpScript = os.getenv('PG_DBUTILS') + '/bin/bcpin.csh'
outputDir = os.getenv('OUTPUTDIR')
statusFileName = outputDir + '/' + statusTable + '.Tumor.bcp'
statusFile = open(statusFileName, 'w')
outFileName = outputDir + '/Tumor.txt'
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

journals = [
'Cancer Cell',
'Cancer Discov',
'Cancer Lett',
'Cancer Res',
'Carcinogenesis',
'Int J Cancer',
'J Natl Cancer Inst',
'Leukemia',
'Mol Cancer Res',
'Nat Rev Cancer',
'Oncogene',
'Semin Cancer Biol'
]

#
# for all journals, search extraced text, except reference section using debbie's ignore set
# for other journals, search title and abstract for searchTerms
#

#
# for this list of journals, search extraced text, except reference section
#
sql = '''
select c._refs_key, c.mgiid, c.pubmedid, s._group_key, lower(d.extractedText) as extractedText
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
and c.journal in (
'Cancer Cell',
'Cancer Discov',
'Cancer Lett',
'Cancer Res',
'Carcinogenesis',
'Int J Cancer',
'J Natl Cancer Inst',
'Leukemia',
'Mol Cancer Res',
'Nat Rev Cancer',
'Oncogene',
'Semin Cancer Biol'
)
order by mgiid desc
'''

results = db.sql(sql, 'auto')
for r in results:

        refKey = r['_refs_key']
        mgiid = r['mgiid']
        pubmedid = r['pubmedid']
        groupKey = r['_group_key']
        termKey = notroutedKey
        term = 'Not Routed'

        print()
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
                print(s, '[', subText, ']')
                allSubText.append(subText)
                matchesTerm += 1

        print(mgiid, pubmedid, term, matchesTerm)

        statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
                % (statusKey, refKey, groupKey, termKey, isCurrent, \
                              userKey, userKey, loaddate, loaddate))

        outFile.write(mgiid + '|' + pubmedid + '|' + term + '|' + str(matchesTerm) + '|' + '|'.join(allSubText) + '\n')

        statusKey += 1

        # set the existing isCurrent = 0
        allIsCurrentSQL += setIsCurrentSQL % (refKey)

statusFile.flush()
statusFile.close()
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
