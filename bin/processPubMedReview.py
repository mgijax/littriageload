#
# The purpose of this script is to:
#
#       1. query the database for references:
#               bib_citation_cache.pubmedid is not null
#               bib_refs.isreviewarticle = 0
#               bib_workflow_tag does not exists for either
#                       MGI:PT-Review_UpdatedAtPubmed  (96651132)
#               bib_refs.year >= current year - 3
#               bib_workflow_data:
#                       this review : entire body
#                       we review   : entire body
#                       minireview  : entire body
#                       mini-review : entire body
#                       review      : first 200 characters
#
#       2. if pubmed publication type = 'Review'
#               set bib_refs.isreviewarticle = 1
#               add MGI:PT_Review_Status_Checked tag
#
 
import sys 
import os
import db
import mgi_utils
import PubMedAgent

db.setTrace()

pma = PubMedAgent.PubMedAgentMedline()

updateReview = '''update BIB_Refs set isReviewArticle = 1 where _Refs_key = %s;\n'''
addTag = '''insert into BIB_Workflow_Tag values(nextval('bib_workflow_tag_seq'),%s,96651132,1001,1001,now(),now());\n'''

updateReviewSQL = ""
addTagSQL = ""

yesCounter = 0;
noCounter = 0;

currentYear = mgi_utils.date('%Y')

# primary query

sql = '''
select b._refs_key, b.mgiid, b.pubmedid, r.isreviewarticle, b.relevanceterm, r.year, r.creation_date, u.login
into temp table tmp_pubmedreview
from bib_citation_cache b, bib_refs r, mgi_user u
where b._refs_key = r._refs_key
and b.relevanceterm = 'keep'
and b.pubmedid is not null
and r.isreviewarticle = 0
and r._createdby_key = u._user_key
and not exists (select 1 from BIB_Workflow_Tag t where b._refs_key = t._refs_key and t._tag_key in (96651132))
and r.year >= %s - 3
''' % (currentYear)
db.sql(sql, None) 
db.sql('create index tmp_idxpubmedreview on tmp_pubmedreview(_refs_key)', None);

# union each search term

sql = '''
select * from tmp_pubmedreview b
where exists (select 1 from bib_workflow_data wfd
        where b._refs_key = wfd._refs_key
        and wfd._extractedtext_key = 48804490
        and wfd.extractedtext ilike '%this review%'
)
union
select * from tmp_pubmedreview b
where exists (select 1 from bib_workflow_data wfd
        where b._refs_key = wfd._refs_key
        and wfd._extractedtext_key = 48804490
        and wfd.extractedtext ilike '%we review%'
)
union
select * from tmp_pubmedreview b
where exists (select 1 from bib_workflow_data wfd
        where b._refs_key = wfd._refs_key
        and wfd._extractedtext_key = 48804490
        and wfd.extractedtext ilike '%minireview%'
)
union
select * from tmp_pubmedreview b
where exists (select 1 from bib_workflow_data wfd
        where b._refs_key = wfd._refs_key
        and wfd._extractedtext_key = 48804490
        and wfd.extractedtext ilike '%mini-review%'
)
union
select * from tmp_pubmedreview b
where exists (select 1 from bib_workflow_data wfd 
        where b._refs_key = wfd._refs_key 
        and wfd._extractedtext_key = 48804490
        and substring(wfd.extractedtext,1,200) ilike '%review%'
)
order by pubmedid
'''

results = db.sql(sql, 'auto')
sys.stdout.flush()

for r in results:

        print('')
        print('pubmedid =', r['pubmedid'], '_refs_key =', r['_refs_key'], 'creation_date =', r['creation_date'], 'year =', r['year'])
        sys.stdout.flush()

        try:
                pubMedRef = pma.getReferenceInfo(r['pubmedid'])
                print('pubmedid =', r['pubmedid'], 'year =', r['year'], 'publication type =', pubMedRef.getPublicationType())
                sys.stdout.flush()

                if pubMedRef.getPublicationType() == 'Review':
                        yesCounter += 1
                        updateReviewSQL += updateReview % (r['_refs_key'])
                        addTagSQL += addTag % (r['_refs_key'])
                else:
                        noCounter += 1
                        continue

        except:
                print('pma.getReferenceInfo unknown error: ', r['pubmedid'])


print('')
print('updateReviewSQL:\n', updateReviewSQL);
print('addTagSQL:\n', addTagSQL);
print('total # of references found: ', len(results))
print('total # of review to update: ', yesCounter)
sys.stdout.flush()
#if updateReviewSQL != "":
#        db.sql(updateReviewSQL, None)
#        db.sql(addTagSQL, None)
db.commit()

