#
#  Originally written by Jim/modified to conform more with our python style
#
#  Purpose:
#
#  1. select references where relevanceStatus = "Not Specified" (70594668)
#
#  2. creates input file for relenvace classifier/predicter
#
#    Data transformations include:
#    replacing non-ascii chars with ' '
#    replacing FIELDSEP and RECORDSEP chars in the doc text w/ ' '
#
#  Outputs:  
#
#        Delimited file to ${NOTSPECIFIED_RELEVANCE}
#       See sampleDataLib.PrimTriageUnClassifiedSample for output format
#

import sys
import os
import re
import db
import sampleDataLib
import ExtractedTextSet

# for the Sample output file
sampleObjType   = sampleDataLib.PrimTriageUnClassifiedSample
outputSampleSet = sampleDataLib.SampleSet(sampleObjType=sampleObjType)

RECORDEND = outputSampleSet.getRecordEnd()
FIELDSEP = sampleObjType.getFieldSep()

# match non-ascii chars
nonAsciiRE = re.compile(r'[^\x00-\x7f]')	

# depends on "tmp_refs" temp table
cmd = '''
create temporary table tmp_refs as
select r._refs_key, c.mgiid, r.title, r.abstract
    from bib_refs r, bib_citation_cache c, bib_workflow_relevance wr
    where r._refs_key = c._refs_key
    and r._refs_key = wr._refs_key
    and wr._relevance_key = 70594668
    and wr.isCurrent = 1;
'''

#
# clean the text fields
#
def cleanUpTextField(rcd, textFieldName):

    # 2to3 note: rcd is not a python dict,
    # it has a has_key() method
    if rcd.has_key(textFieldName):      
        text = str(rcd[textFieldName])
    else:
        text = ''

    # remove RECORDEND and FIELDSEP from text (replace w/ ' ')
    text = text.replace(RECORDEND, ' ').replace(FIELDSEP, ' ')

    # remove non ascii
    text = nonAsciiRE.sub(' ', text)

    return text

#
# MAIN
#

db.setTrace()

fp = open(os.getenv('NOTSPECIFIED_RELEVANCE'), 'w')

# get the results
db.sql(cmd, None)
db.sql('create index tmp_idx1 on tmp_refs(_refs_key)', None)
results = db.sql('select * from tmp_refs', 'auto')

# get their extracted text & add it to results
extTextSet = ExtractedTextSet.getExtractedTextSetForTable(db, 'tmp_refs')
extTextSet.joinRefs2ExtText(results, allowNoText=True)

# create records and add to outputSampleSet
for r in results:

    newR = {}
    newR['ID'] = str(r['mgiid'])
    newR['title'] = cleanUpTextField(r, 'title')
    newR['abstract'] = cleanUpTextField(r, 'abstract')
    newR['extractedText'] = cleanUpTextField(r, 'ext_text')

    newSample = sampleObjType()
    newSample.setFields(newR)
    outputSampleSet.addSample(newSample)

# write sample file
#outputSampleSet.setMetaItem('host', os.getenv('MGD_DBSERVER'))
#outputSampleSet.setMetaItem('db', os.getenv('MGD_DBNAME'))
outputSampleSet.write(fp)
fp.close()
db.commit()

