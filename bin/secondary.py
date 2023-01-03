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
# GXD Criteria : Florida 2 Project
# see processGXD; uses GXD2aryRouter
# 
# QTL Criteria
# References: relevance status = "keep", QTLstatus = "New"
# text to search: extracted text except reference section
# text to look for: 'qtl' (case insensitive)
#
# Tumor Criteria
# References: relevance status = "keep", Tumor status = "New"
# References: relevance status = "discard", confidence > -1.0
# text to search: extracted text except reference section
# text criteria: exclude list (vocab_key 164). (case insensitive)
# if number of text matches <= 9, then Status = Not Routed
# if number of text matches >= 10, then Status = Routed
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
# if number of text matches <= 3, then Status = Not Routed
# if number of text matches >= 4, then Status = Routed
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
import shutil
import db
import mgi_utils
import loadlib
import reportlib

import GXD2aryRouter
import utilsLib

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
                select distinct lower(d.extractedText) as extractedText
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
                logSummary = {}
                searchSummary = {}
                excludeSummary = {}
                totalMatchesTerm = 0
                totalMatchesExcludedTerm = 0
                matchExtractedText = 1

                # if reference is reviewed and group in (AP, GXD, PRO), then set Status = Not Routed
                if isReviewed == 1 and groupKey in (31576664,31576665,78678148):
                        matchExtractedText = 0

                if matchExtractedText == 1:

                        eresults = db.sql(extractedSql % (refKey), 'auto')

                        for e in eresults:
                                matchesExcludedTerm = 0
                                extractedText = e['extractedText']
                                extractedText = extractedText.replace('\n', ' ')
                                extractedText = extractedText.replace('\r', ' ')

                                # iterate thru each search term
                                for s in searchTerms:

                                        # if the search term is found in the extracted text
                                        for match in re.finditer(s, extractedText):

                                                subText = extractedText[match.start()-50:match.end()+50]
                                                matchesExcludedTerm = 0

                                                # iterate thru each exclude term
                                                for e in excludedTerms:

                                                        subText = subText.replace('(', ' ') 
                                                        subText = subText.replace(')', ' ') 
                                                        e = e.replace('(', ' ') 
                                                        e = e.replace(')', ' ') 

                                                        # if the exclude term is found in the subText
                                                        for match2 in re.finditer(e, subText):
                                                                matchesExcludedTerm = 1

                                                                # counts by excludeTerm
                                                                if e not in excludeSummary:
                                                                        excludeSummary[e] = []
                                                                excludeSummary[e].append(subText)

                                                # if matches excluded term, don't change to "Routed"
                                                if matchesExcludedTerm == 0:
                                                        termKey = routedKey;
                                                        term = 'Routed'
                                                        totalMatchesTerm += 1
                                                else:
                                                        totalMatchesExcludedTerm += 1
                                                
                                                # don't show duplicates
                                                key = s + ' [ ' + subText + ']'
                                                value = 'excluded term = ' + str(matchesExcludedTerm)
                                                if key not in logSummary:
                                                        logSummary[key] = [];
                                                        logSummary[key].append(value)

                                                # counts by searchTerm
                                                if s not in searchSummary:
                                                        searchSummary[s] = []
                                                searchSummary[s].append(subText)

                                                allSubText.append(subText)

                # if group in (Tumor) and total match <= 9
                if groupKey == 31576667 and totalMatchesTerm <= 9:
                        termKey = notroutedKey
                        term = 'Not Routed'

                # if group in (PRO) and total match <= 3
                if groupKey == 78678148 and totalMatchesTerm <= 3:
                        termKey = notroutedKey
                        term = 'Not Routed'

                for s in logSummary:
                        logFile.write(str(s) + ' ' + str(logSummary[s][0]) + '\n')

                # counts by searchTerm
                logFile.write('search summary: pubmedid:' + str(pubmedid) + ' ')
                for s in searchSummary:
                    logFile.write(s + '(' + str(len(searchSummary[s])) + ') ')
                logFile.write('\n')

                # counts by excludedTerm
                logFile.write('exclude summary: pubmedid:' + str(pubmedid) + ' ')
                for s in excludeSummary:
                    logFile.write(s + '(' + str(len(excludeSummary[s])) + ') ')
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
        if len(allIsCurrentSql) > 0:
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

        process((sql + orderBy) % (31576667))

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
        secondaryFileName = 'secondary.PRO.log'
        logFileName = logDir + '/' + secondaryFileName
        logFile = open(logFileName, 'w')
        reportlib.header(logFile)
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

        process((sql + orderBy) % (78678148))

        logFile.flush()
        logFile.close()
        outputFile.flush()
        outputFile.close()

        # copy log file to QC/pro folder
        try:
                archiveFile = os.getenv('QCREPORTDIR') + '/archive/pro/' + secondaryFileName + '.' + mgi_utils.date('%Y%m%d.%H%M')
                shutil.copy(logFileName, archiveFile);
        except:
                pass

        return 0

def processGXD():
        # process GXD

        global statusFileName, statusFile
        global logFileName, logFile
        global bcpCmd
        global statusKey

        statusFileName = outputDir + '/' + statusTable + '.GXD.bcp'
        statusFile = open(statusFileName, 'w')
        logFileName = logDir + '/gxd/secondary.GXD.log'
        logFile = open(logFileName, 'w')
        bcpCmd.append('%s %s "/" %s %s' % (bcpI, statusTable, statusFileName, bcpII))

        processGXDRouter()
        processGXDReviewArticle()

        logFile.flush()
        logFile.close()

        return 0

def processGXDRouter():
        # uses GXD2aryRouter instead of SQL logic

        global statusFileName, statusFile
        global logFileName, logFile
        global allIsCurrentSql
        global statusKey

        detailsFileName = logDir + '/gxd/Details.txt'
        detailsFile = open(detailsFileName, 'w')
        routingsFileName = logDir + '/gxd/Routings.txt'
        routingsFile = open(routingsFileName, 'w')
        cat1MatchesFileName = logDir + '/gxd/Cat1Matches.txt'
        cat1MatchesFile = open(cat1MatchesFileName, 'w')
        cat2MatchesFileName = logDir + '/gxd/Cat2Matches.txt'
        cat2MatchesFile = open(cat2MatchesFileName, 'w')
        ageMatchesFileName = logDir + '/gxd/AgeMatches.txt'
        ageMatchesFile = open(ageMatchesFileName, 'w')
        ageExcludesFileName = logDir + '/gxd/AgeExcludes.txt'
        ageExcludesFile = open(ageExcludesFileName, 'w')

        logFile.write('step 1: build the vocabularies\n')

        #
        # 184 | Lit Triage GXD Secondary Journals skipped
        # 166 | Lit Triage GXD Category 1 Terms
        # 135 | Lit Triage GXD Category 1 Exclude
        # 181 | Lit Triage GXD Age Excluded
        # 183 | Lit Triage GXD Category 2 Terms
        # 182 | Lit Triage GXD Category 2 Exclude
        #

        skipJournals = []
        cat1Terms = []
        cat1Exclude = []
        ageExclude = []
        cat2Terms = []
        cat2Exclude = []

        results = db.sql('select term from voc_term where _vocab_key = 184', 'auto')
        for r in results:
                skipJournals.append(r['term'])

        results = db.sql('select term from voc_term where _vocab_key = 166', 'auto')
        for r in results:
                cat1Terms.append(r['term'])

        results = db.sql('select term from voc_term where _vocab_key = 135', 'auto')
        for r in results:
                cat1Exclude.append(r['term'])

        results = db.sql('select term from voc_term where _vocab_key = 181', 'auto')
        for r in results:
                ageExclude.append(r['term'])

        results = db.sql('select term from voc_term where _vocab_key = 183', 'auto')
        for r in results:
                cat2Terms.append(r['term'])

        results = db.sql('select term from voc_term where _vocab_key = 182', 'auto')
        for r in results:
                cat2Exclude.append(r['term'])

        # instantiate the Router class
        router = GXD2aryRouter.GXDrouter(
                skipJournals,   # [journal names] whose articles don't route
                cat1Terms,      # [category 1 terms]
                cat1Exclude,    # [category 1 exclude terms]
                ageExclude,     # [age exclude terms]
                cat2Terms,      # [category 2 terms]
                cat2Exclude,    # [category 2 exclude terms]
                )

        # Details report - summarized all the vocabs, regex, used by the router (GXDrouter has a getExplanation() method)
        detailsFile.write(mgi_utils.date() + '\n')
        detailsFile.write(router.getExplanation())
        detailsFile.flush()
        detailsFile.close()

        logFile.write('step 2: start building report\n')

        # Routings report
        routingsFile.write(mgi_utils.date() + '\n')
        routingsFile.write('MGI_ID|pubmedID|routing|goodJournal|Cat1 matches|Cat1 Excludes|Age matches|Age Excludes|Cat2 matches|Cat2 Excludes|relevance|confidence|isReviewArticle|journal\n')

        # Cat1Matches report
        cat1MatchesFile.write(mgi_utils.date() + '\n')
        cat1MatchesFile.write('MGI_ID|pubmedID|routing|Cat1 matches|matchType|preText|matchText|postText|relevance|confidence\n')

        # Cat2Matches report
        cat2MatchesFile.write(mgi_utils.date() + '\n')
        cat2MatchesFile.write('MGI_ID|pubmedID|routing|Cat2 matches|matchType|preText|matchText|postText|relevance|confidence\n')

        # AgeMatches report
        ageMatchesFile.write(mgi_utils.date() + '\n')
        ageMatchesFile.write('MGI_ID|pubmedID|routing|Age matches|matchType|preText|matchText|postText|relevance|confidence\n')

        # AgeExcludes report
        ageExcludesFile.write(mgi_utils.date() + '\n')
        ageExcludesFile.write('MGI_ID|pubmedID|routing|Age excludes|matchType|preText|matchText|postText|relevance|confidence\n')

        logFile.write('step 3: search the database for references that match criteria\n')

        #
        # search criteria
        #
        #       group = GXD
        #       isCurrent = 1
        #       relevance = discard
        #       status = New
        #       user = relevance_classifier
        #       confidence > -2.75
        #       _extractedtext_key != reference (48804491)
        #       isReviewArticle = 0
        #       extractedText is not null
        #
        #       relevance = discard must be one row 1 (isCurrent = 1)
        #        user = relevance_classifier/confidence > -2.75 can be on *any* line
        #
        #       union
        #
        #       group = GXD
        #       isCurrent = 1
        #       relevance = keep
        #       status = New
        #       _extractedtext_key != reference (48804491)
        #       isReviewArticle = 0
        #       extractedText is not null
        #
        # for each reference:
        #       step 5: concatenate all extracted text for this reference and then send to route
        #       step 6: send to router
        #       step 7: generate report log
        #       step 8: set GXD Status = Routed or Not Routed
        #
        #
        #  step 9: group = GXD, status = New, reviewArticle = yes, set to Not Routed
        #

        results = db.sql('''
                (
                select c._refs_key, c.mgiid, c.pubmedid, c.isreviewarticlestring, 
                        s._group_key, r.journal, t.term as relevanceTerm, v.confidence
                from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s, voc_term t
                where r._refs_key = c._refs_key
                and c.isReviewArticle = 0
                and r._refs_key = v._refs_key
                and v.isCurrent = 1
                and v._relevance_key = 70594666
                and v._relevance_key = t._term_key
                and exists (select 1 from bib_workflow_relevance vv
                        where r._refs_key = vv._refs_key
                        and vv._modifiedby_key = 1617
                        and vv.confidence > -2.75
                        )
                and r._refs_key = s._refs_key
                and s._status_key = 71027551
                and s._group_key = 31576665
                and s.isCurrent = 1
                and exists (select 1 from bib_workflow_data d
                        where r._refs_key = d._refs_key
                        and d._extractedtext_key != 48804491
                        and d.extractedText is not null
                        )
                union
                select c._refs_key, c.mgiid, c.pubmedid, c.isreviewarticlestring, 
                        s._group_key, r.journal, t.term as relevanceTerm, v.confidence
                from bib_citation_cache c, bib_refs r, bib_workflow_relevance v, bib_workflow_status s, voc_term t
                where r._refs_key = c._refs_key
                and c.isReviewArticle = 0
                and r._refs_key = v._refs_key
                and v.isCurrent = 1
                and v._relevance_key = 70594667
                and v._relevance_key = t._term_key
                and r._refs_key = s._refs_key
                and s._status_key = 71027551
                and s._group_key = 31576665
                and s.isCurrent = 1
                and exists (select 1 from bib_workflow_data d
                        where r._refs_key = d._refs_key
                        and d._extractedtext_key != 48804491
                        and d.extractedText is not null
                        )
                )
                order by pubmedid desc
        ''', 'auto')

        logFile.write('step 4: iterate thru references\n')

        for r in results:

                # pubmed id may be null
                if r['pubmedid'] == None:
                        r['pubmedid'] = ""

                logFile.write('\n' + r['mgiid'] + '|' + r['pubmedid'] + '|' + r['journal'] + '\n')

                logFile.write('step 5: concatenate all extracted text for this reference and then send to route\n')
                eresults = db.sql('''
                        select extractedtext
                        from bib_workflow_data
                        where _refs_key = %s
                        and _extractedtext_key != 48804491
                        and extractedtext is not null
                ''' % (r['_refs_key']), 'auto')
                extractedText = ""
                for e in eresults:
                        extractedText += e['extractedText'] + '\n'

                logFile.write('step 6: send to router\n')
                routing = router.routeThisRef(extractedText, r['journal'])

                logFile.write('step 7: generate report log\n')

                if router.getGoodJournal() == 1:
                        goodJournal = "Yes"
                else:
                        goodJournal = "No"

                # Routing report
                routingsFile.write(r['mgiid'] + '|' + r['pubmedid'] + '|' + routing + '|' + goodJournal + '|')
                routingsFile.write(str(len(router.getCat1Matches())) + '|')
                routingsFile.write(str(len(router.getCat1Excludes())) + '|')
                routingsFile.write(str(len(router.getAgeMatches())) + '|')
                routingsFile.write(str(len(router.getAgeExcludes())) + '|')
                routingsFile.write(str(len(router.getCat2Matches())) + '|')
                routingsFile.write(str(len(router.getCat2Excludes())) + '|')
                routingsFile.write(r['relevanceTerm'] + '|' + str(r['confidence']) + '|' + r['isreviewarticlestring'] + '|' + r['journal'] + '\n')

                # Cat1 Matches
                for c in router.getCat1Matches():
                        cat1MatchesFile.write(r['mgiid'] + '|' + r['pubmedid'] + '|' + routing + '|')
                        cat1MatchesFile.write(str(len(router.getCat1Matches())) + '|')
                        cat1MatchesFile.write(c.matchType + '|')
                        cat1MatchesFile.write(c.preText.replace('\n','\\n').replace('\t','\\t') + '|')
                        cat1MatchesFile.write(c.matchText.replace('\n','\\n').replace('\t','\\t') + '|')
                        cat1MatchesFile.write(c.postText.replace('\n','\\n').replace('\t','\\t') + '|')
                        cat1MatchesFile.write(r['relevanceTerm'] + '|' + str(r['confidence']) + '\n')

                # Cat2 Matches
                for c in router.getCat2Matches():
                        cat2MatchesFile.write(r['mgiid'] + '|' + r['pubmedid'] + '|' + routing + '|')
                        cat2MatchesFile.write(str(len(router.getCat2Matches())) + '|')
                        cat2MatchesFile.write(c.matchType + '|')
                        cat2MatchesFile.write(c.preText.replace('\n','\\n').replace('\t','\\t') + '|')
                        cat2MatchesFile.write(c.matchText.replace('\n','\\n').replace('\t','\\t') + '|')
                        cat2MatchesFile.write(c.postText.replace('\n','\\n').replace('\t','\\t') + '|')
                        cat2MatchesFile.write(r['relevanceTerm'] + '|' + str(r['confidence']) + '\n')

                # Age Matches
                for c in router.getAgeMatches():
                        ageMatchesFile.write(r['mgiid'] + '|' + r['pubmedid'] + '|' + routing + '|')
                        ageMatchesFile.write(str(len(router.getAgeMatches())) + '|')
                        ageMatchesFile.write(c.matchType + '|')
                        ageMatchesFile.write(c.preText.replace('\n','\\n').replace('\t','\\t') + '|')
                        ageMatchesFile.write(c.matchText.replace('\n','\\n').replace('\t','\\t') + '|')
                        ageMatchesFile.write(c.postText.replace('\n','\\n').replace('\t','\\t') + '|')
                        ageMatchesFile.write(r['relevanceTerm'] + '|' + str(r['confidence']) + '\n')

                # Age Excludes
                for c in router.getAgeExcludes():
                        ageExcludesFile.write(r['mgiid'] + '|' + r['pubmedid'] + '|' + routing + '|')
                        ageExcludesFile.write(str(len(router.getAgeMatches())) + '|')
                        ageExcludesFile.write(c.matchType + '|')
                        ageExcludesFile.write(c.preText.replace('\n','\\n').replace('\t','\\t') + '|')
                        ageExcludesFile.write(c.matchText.replace('\n','\\n').replace('\t','\\t') + '|')
                        ageExcludesFile.write(c.postText.replace('\n','\\n').replace('\t','\\t') + '|')
                        ageExcludesFile.write(r['relevanceTerm'] + '|' + str(r['confidence']) + '\n')

                if routing == "Yes":
                        termKey = routedKey;
                        logFile.write('step 8: set GXD Status = Routed\n')
                else:
                        termKey = notroutedKey;
                        logFile.write('step 8: set GXD Status = Not Route\n')

                statusFile.write('%s|%s|31576665|%s|%s|%s|%s|%s|%s\n' \
                          % (statusKey, r['_refs_key'], termKey, isCurrent, userKey, userKey, loaddate, loaddate))
                statusKey += 1

                # set the existing isCurrent = 0
                allIsCurrentSql += setIsCurrentSql % (r['_group_key'], r['_refs_key'])

        routingsFile.flush()
        routingsFile.close()
        cat1MatchesFile.flush()
        cat1MatchesFile.close()
        cat2MatchesFile.flush()
        cat2MatchesFile.close()
        ageMatchesFile.flush()
        ageMatchesFile.close()
        ageExcludesFile.flush()
        ageExcludesFile.close()

        return 0

def processGXDReviewArticle():
        # process gxd review articles

        global statusFileName, statusFile
        global logFileName, logFile
        global allIsCurrentSql
        global statusKey

        #
        # search criteria
        #
        #       group = GXD
        #       status = New
        #       isReviewArticle = 1
        #
        results = db.sql('''
                select c._refs_key, c.mgiid, c.pubmedid, s._group_key, r.journal
                from bib_citation_cache c, bib_refs r, bib_workflow_status s
                where r._refs_key = c._refs_key
                and c.isReviewArticle = 1
                and r._refs_key = s._refs_key
                and s._status_key = 71027551
                and s._group_key = 31576665
                and s.isCurrent = 1
                order by pubmedid desc
        ''', 'auto')

        logFile.write('\nstep 9: group = GXD, status = New, reviewArticle = Yes, set status = Not Routed\n')

        for r in results:

                # pubmed id may be null
                if r['pubmedid'] == None:
                        r['pubmedid'] = ""

                logFile.write('\n' + r['mgiid'] + '|' + r['pubmedid'] + '|' + r['journal'] + '\n')

                termKey = notroutedKey;
                statusFile.write('%s|%s|31576665|%s|%s|%s|%s|%s|%s\n' \
                          % (statusKey, r['_refs_key'], termKey, isCurrent, userKey, userKey, loaddate, loaddate))
                statusKey += 1
                
                # set the existing isCurrent = 0
                allIsCurrentSql += setIsCurrentSql % (r['_group_key'], r['_refs_key'])

        return 0

#
#  MAIN
#

#print('initialize')
if initialize() != 0:
    sys.exit(1)

#print('processAP')
if processAP() != 0:
    sys.exit(1)

#print('processQTL')
if processQTL() != 0:
    sys.exit(1)

#print('processTumor')
if processTumor() != 0:
    sys.exit(1)

#print('processGO')
if processGO() != 0:
    sys.exit(1)

#print('processPRO')
if processPRO() != 0:
    sys.exit(1)

#print('processGXD')
if processGXD() != 0:
    sys.exit(1)

# flush the status 
statusFile.flush()
statusFile.close()

#print('bcpFiles')
if bcpFiles() != 0:
    sys.exit(1)

sys.exit(0)

