#!/usr/bin/env python3

#-----------------------------------
'''
  Purpose:
    run sql to get references with relevanceStatus = "no specified"
    so they can be run through the relevanceClassifier and prediced
    "keep" or "discard".

    (minor) Data transformations include:
    replacing non-ascii chars with ' '
    replacing FIELDSEP and RECORDSEP chars in the doc text w/ ' '

  Outputs:  Delimited file to stdout
            See sampleDataLib.PrimTriageUnClassifiedSample for output format
'''
#-----------------------------------
import sys
import os
import string
import re
import time
import argparse
import db
import sampleDataLib
import ExtractedTextSet
#-----------------------------------

def getArgs():

    parser = argparse.ArgumentParser( \
        description='Get refs whose relevanceStatus needs to be predicted by the relevanceClassifier, write sample file to stdout')

    parser.add_argument('--test', dest='test', action='store_true',
        required=False,
        help="just run ad hoc test code")

    parser.add_argument('-l', '--limit', dest='nResults',
        required=False, type=int, default=0, 		# 0 means ALL
        help="limit SQL to n results. Default is no limit")

    parser.add_argument('--textlength', dest='maxTextLength',
        type=int, required=False, default=None,
        help="only include the 1st n chars of text fields (for debugging)")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    defaultHost = os.environ.get('PG_DBSERVER', 'bhmgidevdb01')
    defaultDatabase = os.environ.get('PG_DBNAME', 'prod')

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default=defaultHost,
        help='db server. Shortcuts:  adhoc, prod, dev, test. (Default %s)' %
                defaultHost)

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default=defaultDatabase,
        help='which database. Example: mgd (Default %s)' % defaultDatabase)

    args =  parser.parse_args()

    if args.server == 'adhoc':
        args.host = 'mgi-adhoc.jax.org'
        args.db = 'mgd'
    elif args.server == 'prod':
        args.host = 'bhmgidb01.jax.org'
        args.db = 'prod'
    elif args.server == 'dev':
        args.host = 'mgi-testdb4.jax.org'
        args.db = 'jak'
    elif args.server == 'test':
        args.host = 'bhmgidevdb01.jax.org'
        args.db = 'prod'
    else:
        args.host = args.server + '.jax.org'
        args.db = args.database

    return args
#-----------------------------------

args = getArgs()
#-----------------------------------

# for the Sample output file
sampleObjType   = sampleDataLib.PrimTriageUnClassifiedSample
outputSampleSet = sampleDataLib.SampleSet(sampleObjType=sampleObjType)

RECORDEND    = outputSampleSet.getRecordEnd()
FIELDSEP     = sampleObjType.getFieldSep()

# SQL to get the required reference records into a tmp table
#   (w/o their extracted text)
if args.nResults > 0: limitClause = 'limit %d' % args.nResults
else: limitClause = ''

SQL = [
    '''
    create temporary table tmp_refs
    as
    select distinct r._refs_key,
        a.accid mgiid,
        r.title,
        r.abstract
    from bib_refs r 
        join bib_workflow_relevance br on
                            (r._refs_key = br._refs_key and br.iscurrent = 1)
        join voc_term t on (br._relevance_key = t._term_key)
        join acc_accession a on
             (a._object_key = r._refs_key and a._logicaldb_key = 1
              and a._mgitype_key=1 and a.preferred=1 and a.prefixpart = 'MGI:')
    where 
       t.term = 'Not Specified'
    %s  -- limit clause if any
    ''' % limitClause,
    '''
    create index tmp_idx1 on tmp_refs(_refs_key)
    ''',
    ]

####################
def main():
####################
    db.set_sqlServer  ( args.host)
    db.set_sqlDatabase( args.db)
    db.set_sqlUser    ("mgd_public")
    db.set_sqlPassword("mgdpub")

    verbose( "Hitting database %s %s as mgd_public\n" % (args.host, args.db))
    startTime = time.time()

    # build tmp table tmp_refs: reference records that need predicting
    results = db.sql(SQL, 'auto')

    # get the rcds
    refRecords =  db.sql(['select * from tmp_refs'], 'auto')[-1]

    # get their extracted text & add it to refRecords
    extTextSet = ExtractedTextSet.getExtractedTextSetForTable(db, 'tmp_refs')
    extTextSet.joinRefs2ExtText(refRecords, allowNoText=True)

    # create Sample records and add to outputSampleSet
    for r in refRecords:
        sample = sqlRecord2UnClassifiedSample(r)
        outputSampleSet.addSample(sample)

    # write Sample file to stdout
    nResults = writeSamples(outputSampleSet)

    verbose("%d References written\n" % outputSampleSet.getNumSamples())
    verbose("Total time: %8.3f seconds\n\n" % (time.time()-startTime))
#-----------------------------------

def writeSamples(sampleSet):
    sampleSet.setMetaItem('host', args.host)
    sampleSet.setMetaItem('db', args.db)
    sampleSet.setMetaItem('time', time.strftime("%Y/%m/%d-%H:%M:%S"))
    sampleSet.write(sys.stdout)
#-----------------------------------

def sqlRecord2UnClassifiedSample( r,		# sql Result record
    ):
    """
    Encapsulates knowledge of UnClassifiedSample.setFields() field names
    """
    newR = {}
    newSample = sampleObjType()

    newR['ID']            = str(r['mgiid'])
    newR['title']         = cleanUpTextField(r, 'title')
    newR['abstract']      = cleanUpTextField(r, 'abstract')
    newR['extractedText'] = cleanUpTextField(r, 'ext_text')

    return newSample.setFields(newR)
#-----------------------------------

def cleanUpTextField(rcd,
                    textFieldName,
    ):
    # in case we omit this text field during debugging, check if defined
    if rcd.has_key(textFieldName):      # 2to3 note: rcd is not a python dict,
                                        #  it has a has_key() method
        text = str(rcd[textFieldName])
    else: text = ''

    if args.maxTextLength:	# handy for debugging
        text = text[:args.maxTextLength]
        text = text.replace('\n', ' ') + '\n'   # just keep one \n at end

    text = removeNonAscii(cleanDelimiters(text))
    return text
#-----------------------------------

def cleanDelimiters(text):
    """ remove RECORDEND and FIELDSEPs from text (replace w/ ' ')
    """
    new = text.replace(RECORDEND,' ').replace(FIELDSEP,' ')
    return new
#-----------------------------------

nonAsciiRE = re.compile(r'[^\x00-\x7f]')	# match non-ascii chars
def removeNonAscii(text):
    return nonAsciiRE.sub(' ',text)
#-----------------------------------

def verbose(text):
    if args.verbose:
        sys.stderr.write(text)
        sys.stderr.flush()
#-----------------------------------

if __name__ == "__main__":
    if not (len(sys.argv) > 1 and sys.argv[1] == '--test'):
        main()
    else: 			# ad hoc test code
        if True:
            print('no test cases defined')
