#
#  Purpose:
#
#  secondary triage :
#
#       http://mgiprodwiki/mediawiki/index.php/sw:Secondary_Triage_Loader_Requirements#Tumor_Criteria
#
# AP Criteria
# References: relevance status = "keep", APstatus = "New"
# Is Reviewed = Not Routed
# text to search: extracted text except reference section
# text to look for: (case insensitive)
# 
# GXD Criteria
# References: relevance status = "keep", GXDstatus = "New"
# Is Reviewed = Not Routed
# References: relevance status = "discard", confidence > -1.5
# text to search: extracted text except reference section
# text criteria: '%embryo%' ; exclude list (vocab_key 135). (case insensitive)
# 
# QTL Criteria
# References: relevance status = "keep", QTLstatus = "New"
# text to search: extracted text except reference section
# text to look for: 'qtl' (case insensitive)
#
# Tumor Criteria
# References: relevance status = "keep", Tumor status = "New"
# References: relevance status = "discard", confidence > -1.5
# text to search: extracted text except reference section
# text criteria: exclude list (vocab_key 164). (case insensitive)
# if number of text matches <= 4, then Status = Not Routed
# if number of text matches >= 5, then Status = Routed
#
# GO Criteria
# References: relevance status = "keep", GO status = "New"
# Set all GO status = Not Routed
#
# PRO Criteria
# References: relevance status = "keep", PROstatus = "New"
# Is Reviewed = Not Routed
# text to search: extracted text except reference section
# text criteria: exclude list (vocab_key 170). (case insensitive)
# text to look for: (case insensitive)
#
# logFile = 
#       mgiid, pubmedid, confidence, term, totalMatchesTerm, subText
#
# outputFile = 
#       mgiid, pubmedid, onfidence, term, totalMatchesTerm, matchesExcludedTerm, allSubText
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

results = db.sql(''' select nextval('bib_workflow_status_seq') as maxKey ''', 'auto')
statusKey = results[0]['maxKey']

allIsCurrentSql = ''
setIsCurrentSql = '''update bib_workflow_status set isCurrent = 0 where isCurrent = 1 and _group_key = %s and _refs_key = %s;\n'''

bcpI = '%s %s %s' % (bcpScript, db.get_sqlServer(), db.get_sqlDatabase())
bcpII = '"|" "\\n" mgd'
bcpCmd = []

loaddate = loadlib.loaddate

isCurrent = "1"
routedKey = "31576670"
notroutedKey = "31576669"

searchTerms = []
excludedTerms = []
sql = ''
orderBy = ''
extractedSql = ''

def initialize():
        global sql, orderBy, extractedSql

        # distinct references
        # where relevance = 'keep'
        #       status = "New"
        #       non-reference extracted text exists
        sql = '''
                (
                select c._refs_key, c.mgiid, c.pubmedid, s._group_key, v.confidence, c.isreviewarticle
                from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s
                where r._refs_key = c._refs_key
                and r._refs_key = v._refs_key
                and v.isCurrent = 1
                and v._relevance_key = 70594667
                and r._refs_key = s._refs_key
                and s._status_key = 71027551
                and s._group_key = %s
                and s.isCurrent = 1
                and exists (select 1 from bib_workflow_data d
                        where r._refs_key = d._refs_key
                        and d._extractedtext_key not in (48804491)
                        and d.extractedText is not null
                        )
        '''

        orderBy = ') order by mgiid desc'

        # extracted_text by _refs_key where extracted text type != 'reference'
        extractedSql = '''
                select lower(d.extractedText) as extractedText
                from bib_workflow_data d
                where d._refs_key = %s
                and d._extractedtext_key not in (48804491)
                and d.extractedText is not null
        '''

        return 0

def process(sql):
        global statusFile
        global logFile
        global outputFile
        global allIsCurrentSql
        global statusKey

        # general processing

        countNotRouted = 0
        countRouted = 0

        results = db.sql(sql, 'auto')

        # iterate thru each distinct reference
        for r in results:

                refKey = r['_refs_key']
                mgiid = r['mgiid']
                pubmedid = r['pubmedid']
                groupKey = r['_group_key']
                confidence = r['confidence']
                isReviewed = r['isreviewarticle']
                termKey = notroutedKey
                term = 'Not Routed'

                logFile.write('\n')
                allSubText = []
                matchSummary = {}
                totalMatchesTerm = 0
                totalMatchesExcludedTerm = 0
                matchExtractedText = 1

                # if reference is reviewed and group in (AP, GXD, PRO), then set Status = Not Routed
                if isReviewed == 1 and groupKey in (31576664,31576665,75601866):
                        matchExtractedText = 0

                if matchExtractedText == 1:
                        eresults = db.sql(extractedSql % (refKey), 'auto')
                        for e in eresults:
                                matchesExcludedTerm = 0
                                extractedText = e['extractedText']
                                extractedText = extractedText.replace('\n', ' ')
                                extractedText = extractedText.replace('\r', ' ')

                                for s in searchTerms:
                                        for match in re.finditer(s, extractedText):
                                                exactMatchText = extractedText[match.start()-10:match.end()+10]
                                                subText = extractedText[match.start()-50:match.end()+50]
                                                #if len(subText) == 0:
                                                #        exactMatchText = extractedText[match.start()-10:match.end()+10]
                                                #        subText = extractedText[match.start()-50:match.end()+50]

                                                matchesExcludedTerm = 0
                                                for e in excludedTerms:
                                                        for match2 in re.finditer(e, subText):
                                                                matchesExcludedTerm = 1

                                                # if exactMatchText matches excluded term, don't change to "Routed"
                                                if matchesExcludedTerm == 0:
                                                        termKey = routedKey;
                                                        term = 'Routed'
                                                        totalMatchesTerm += 1
                                                else:
                                                        totalMatchesExcludedTerm += 1
                                                
                                                logFile.write(s + ' [ ' + subText + '] excluded term = ' + str(matchesExcludedTerm) + '\n')

                                                # counts by searchTerm
                                                if s not in matchSummary:
                                                        matchSummary[s] = []
                                                matchSummary[s].append(subText)

                                                allSubText.append(subText)

                # if group in (Tumor) and total match <= 4
                if groupKey == 31576667 and totalMatchesTerm <= 4:
                        termKey = notroutedKey
                        term = 'Not Routed'

                # counts by searchTerm
                logFile.write('summary: pubmedid:' + str(pubmedid) + ' ')
                for s in matchSummary:
                    logFile.write(s + '(' + str(len(matchSummary[s])) + ') ')
                logFile.write('\n')

                logFile.write(mgiid + ' ' + \
                        str(pubmedid) + ' ' + \
                        str(confidence) + ' ' + \
                        term + ' ' + \
                        str(totalMatchesTerm) + ' ' + \
                        'is_review = ' + str(isReviewed) + '\n')

                if termKey == notroutedKey:
                        countNotRouted += 1
                else:
                        countRouted += 1

                statusFile.write('%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
                        % (statusKey, refKey, groupKey, termKey, isCurrent, \
                           userKey, userKey, loaddate, loaddate))

                outputFile.write(mgiid + '|' + \
                        str(pubmedid) + '|' + \
                        str(confidence) + '|' + \
                        term + '|' + \
                        str(totalMatchesTerm) + '|' + \
                        str(totalMatchesExcludedTerm) + '|' + \
                        '|'.join(allSubText) + '\n')

                statusKey += 1

                # set the existing isCurrent = 0
                allIsCurrentSql += setIsCurrentSql % (groupKey, refKey)

        logFile.write('\nNot Routed = ' + str(countNotRouted) + '\n')
        logFile.write('\nRouted = ' + str(countRouted) + '\n')

def bcpFiles():

        # update existing relevance isCurrent = 0
        # must be done *before* the new rows are added
        #print(allIsCurrentSql)
        db.sql(allIsCurrentSql, None)
        db.commit()

        # enter new relevance data
        for b in bcpCmd:
                #print(b)
                os.system(b)
        db.commit()

        # update bib_workflow_status serialization
        db.sql(''' select setval('bib_workflow_status_seq', (select max(_Assoc_key) from BIB_Workflow_Status)) ''', None)
        db.commit()

        return 0

def processAP():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.AP.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.AP.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/AP.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms =[]
        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 165 order by term', 'auto')
        for r in results:
                searchTerms.append(r['term'])
        #print(searchTerms)

        excludedTerms = []
        process((sql + orderBy) % (31576664))

        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        return 0

def processGXD():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.GXD.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.GXD.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/GXD.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = []
        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 166 order by term', 'auto')
        for r in results:
                searchTerms.append(r['term'])
        #print(searchTerms)

        excludedTerms = []
        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 135 order by term', 'auto')
        for r in results:
                excludedTerms.append(r['term'])
        #print(excludedTerms)

        mysql = sql
        mysql = mysql % (31576665) + '\n' + \
        '''
        union
        select c._refs_key, c.mgiid, c.pubmedid, s._group_key, v.confidence, c.isreviewarticle
        from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s
        where r._refs_key = c._refs_key
        and r._refs_key = v._refs_key
        and v.isCurrent = 1
        and v._relevance_key = 70594666
        and v.confidence > -1.5
        and r._refs_key = s._refs_key
        and s._status_key = 71027551
        and s._group_key = 31576665
        and exists (select 1 from bib_workflow_data d
                where r._refs_key = d._refs_key
                and d._extractedtext_key not in (48804491)
                and d.extractedText is not null
                )
        '''
        process(mysql + orderBy)

        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        return 0

def processQTL():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.QTL.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.QTL.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/QTL.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = []
        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 168 order by term', 'auto')
        for r in results:
                searchTerms.append(r['term'])
        #print(searchTerms)

        excludedTerms = []
        process((sql + orderBy) % (31576668))

        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        return 0

def processTumor():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.Tumor.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.Tumor.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/Tumor.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = []
        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 167 order by term', 'auto')
        for r in results:
                searchTerms.append(r['term'])
        #print(searchTerms)

        excludedTerms = []
        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 164 order by term', 'auto')
        for r in results:
                excludedTerms.append(r['term'])
        #print(excludedTerms)

        mysql = sql
        mysql = mysql % (31576667) + '\n' + \
        '''
        union
        select c._refs_key, c.mgiid, c.pubmedid, s._group_key, v.confidence, c.isreviewarticle
        from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s
        where r._refs_key = c._refs_key
        and r._refs_key = v._refs_key
        and v.isCurrent = 1
        and v._relevance_key = 70594666
        and v.confidence > -1.5
        and r._refs_key = s._refs_key
        and s._status_key = 71027551
        and s._group_key = 31576667
        and exists (select 1 from bib_workflow_data d
                where r._refs_key = d._refs_key
                and d._extractedtext_key not in (48804491)
                and d.extractedText is not null
                )
        '''
        process(mysql + orderBy)

        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        return 0

def processGO():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.GO.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.GO.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/GO.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        searchTerms = [] 
        excludedTerms = []
        process((sql + orderBy) % (31576666))

        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        return 0

def processPRO():
        global statusFileName, statusFile
        global logFileName, logFile
        global outputFileName, outputFile
        global searchTerms
        global excludedTerms
        global bcpCmd

        statusFileName = outputDir + '/' + statusTable + '.PRO.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/secondary.PRO.log'
        logFile = open(logFileName, 'w')
        outputFileName = outputDir + '/PRO.txt'
        outputFile = open(outputFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 169 order by term', 'auto')
        for r in results:
                searchTerms.append(r['term'])
        #print(searchTerms)

        results = db.sql('select lower(term) as term from voc_term where _vocab_key = 170 order by term', 'auto')
        for r in results:
                excludedTerms.append(r['term'])
        #print(excludedTerms)

        process((sql + orderBy) % (75601866))

        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        return 0

#
#  MAIN
#

#print('initialize')
if initialize() != 0:
    sys.exit(1)

#print('processAP')
if processAP() != 0:
    closeFiles()
    sys.exit(1)

#print('processGXD')
if processGXD() != 0:
    closeFiles()
    sys.exit(1)

#print('processQTL')
if processQTL() != 0:
    closeFiles()
    sys.exit(1)

#print('processTumor')
if processTumor() != 0:
    closeFiles()
    sys.exit(1)

#print('processGO')
if processGO() != 0:
    closeFiles()
    sys.exit(1)

#print('processPRO')
if processPRO() != 0:
    closeFiles()
    sys.exit(1)

# flush the status 
statusFile.flush()
statusFile.close()

#print('bcpFiles')
if bcpFiles() != 0:
    sys.exit(1)

sys.exit(0)

