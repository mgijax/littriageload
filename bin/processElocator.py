#
# The purpose of this script is to:
#
#       1. query the database for references:
#               bib_citation_cache.pubmedid is not null
#               bib_refs._referencetype = key = 31576687 (Peer Reviewed Article)
#               bib_refs.pgs is null or empty
#               bib_workflow_relevance._relevance_key = 70594667 (keep)
#
#       2. if pubmed 'LID - eXXXXX [pii]' exists where e = 'e' or 'E'
#               set bib_refs.pgs = eXXXXX
#
# find page numbers being stored in LID/[pii] (publisher item identifier)
# this is known as the 'elocator' : XXXX can be anything;alphanumeric; case insensitive
#       eXXX
#       bioXXX
#       devXXX
#       dmmXXX
#       jcsXXX
#
#       if E[0-9]xxx, then remove the E
#

# HISTORY
#
# 01/12/2022    lec
#       https://mgi-jira.atlassian.net/browse/WTS2-599
#       use pubmed/PG or LID to find reference page
#

import sys 
import os
import db
import PubMedAgent

db.setTrace()

pma = PubMedAgent.PubMedAgentMedline()

updatePgs = '''update BIB_Refs set pgs = '%s' where _Refs_key = %s;\n'''
updatePgsSQL = ""

yesCounter = 0;
noCounter = 0;
#and b.pubmedid in ('31779270', '29445765', '29593106')

results = db.sql('''
select b._refs_key, b.mgiid, b.pubmedid, b.doiid, r.journal
from bib_citation_cache b, bib_refs r
where b._refs_key = r._refs_key
and b.pubmedid is not null
and r._referencetype_key = 31576687
and (r.pgs is null or r.pgs = '')
and r.journal in (
'Int J Mol Sci',
'Cells',
'JCI Insight',
'Biomolecules',
'Development',
'eNeuro',
'J Cell Sci',
'Dis Model Mech',
'Biosci Rep',
'Biol Open',
'Elife',
'Endocrinology',
'Cancer Res',
'J Clin Invest',
'J Immunol',
'Proc Natl Acad Sci U S A',
'Am J Physiol Lung Cell Mol Physiol',
'Am J Physiol Cell Physiol',
'J Natl Cancer Inst',
'Am J Physiol Heart Circ Physiol'
)
and exists (select 1 from bib_workflow_relevance v where r._refs_key = v._refs_key and v.isCurrent = 1 and v._relevance_key = 70594667)
order by r.journal
''', 'auto')

sys.stdout.flush()

for r in results:

        pubMedRef = pma.getReferenceInfo(r['pubmedid'])
        print(r['journal'], ' ', r['pubmedid'], ' ', r['mgiid'], ' ', r['doiid'], ' ', ' ', pubMedRef.getElocator())
        sys.stdout.flush()

        if pubMedRef.getElocator():
                yesCounter += 1
                updatePgsSQL += updatePgs % (pubMedRef.getElocator(), r['_refs_key'])
        else:
                noCounter += 1
                continue

print('')
#print('updatePgsSQL:\n', updatePgsSQL);
print('total # of references found: ', len(results))
print('total # of with LID : ', yesCounter)
print('total # of without LID : ', noCounter)
sys.stdout.flush()
if updatePgsSQL != "":
        db.sql(updatePgsSQL, None)
db.commit()

