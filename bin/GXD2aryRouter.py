#!/usr/bin/env python3
'''
  Purpose: Define the classes that implement the GXD 2ary triage routing
            algorithm.
           The main class is GXD2aryRouter.
           To instantiate this class, you need vocabularies (lists of strings)
            for the vocabs listed below.

  To Run Automated Unit Tests:  python test_GXD2aryRouter.py [-v]
  (for low level routines and age matches)
  
  To Use:
    import GXD2aryRouter
    import utilsLib
    ...
    ### instantiate the Router class
    router = GXD2aryRouter.GXDrouter(
                skipJournals,   # [journal names] whose articles don't route
                cat1Terms,      # [category 1 terms]
                cat1Exclude,    # [category 1 exclude terms]
                ageExclude,     # [age exclude terms]
                cat2Terms,      # [category 2 terms]
                cat2Exclude,    # [category 2 exclude terms]
                )
    ### to route a reference, text = extracted text w/o the references section
    routing =  router.routeThisRef(lower(text), journal)
    if routing == 'Yes':
        # route it to GXD...

        # to get all the utilsLib.MatchRcds that describe why it was routed
        matches = router.getAllMatches()

        # (other subsets of getMatches() are supported too)
    else:
        # don't route it to GXD

        # to get all the utilsLib.MatchRcds that describe why it wasn't routed
        matches = router.getExcludeMatches()
'''
import sys
import re
import figureText
from utilsLib import MatchRcd, TextMapping, TextMappingFromStrings, TextTransformer, spacedOutRegex

PARABOUNDARY = '\n\n'        # signifies paragraph boundaries in extracted text
PARABOUNDARY_REGEX = r'\n\n' # regex chars for paragraph boundaries

#-----------------------------------

class GXDrouter (object):
    """
    Is a: object that knows how to route references for GXD 2ary triage
    Has : vocabularies (lists of strings)
            see __init__() below
          list of utilsLib.MatchRcd's for the most recent call to routeThisRef()
    Does: routeThisRef() routes a reference (return 'Yes' or 'No') given the
            reference text and its journal name.
          get MatchRcd's
          get algorithm/vocab summary text
    """
    def __init__(self,
                skipJournals,   # [journal names] whose articles don't route
                                #    case sensitive
                cat1Terms,      # [category 1 terms]
                cat1Exclude,    # [category 1 exclude terms]
                ageExclude,     # [age exclude terms]
                cat2Terms,      # [category 2 terms]
                cat2Exclude,    # [category 2 exclude terms]
                numChars=30,    # n chars on each side of cat1/2 match to report
                ageContext=210, # n chars around age matches to keep & search
                minTextLen=500, # if extracted text len is < this, route it
                ):
        self.numChars = numChars
        self.skipJournals = {j for j in skipJournals} # set of journal names
        self.cat1Terms    = cat1Terms
        self.cat1Exclude  = cat1Exclude
        self.ageExclude   = ageExclude
        self.ageContext   = ageContext
        self.cat2Terms    = cat2Terms
        self.cat2Exclude  = cat2Exclude
        self.minTextLen   = minTextLen

        # figure text extraction: keep figure legends and words around 
        #  "figure/table" in other paragraphs.
        # figure legends are paragraphs that start with "fig", "figure", "table"
        self.numFigTextWords = 75       # n words around "figure/table" in
                                        #   paragraphs to keep as figure text
        self.figTextConverter = figureText.Text2FigConverter( \
                                            conversionType='legCloseWords',
                                            numWords=self.numFigTextWords)
        self._buildCat1Detection()
        self._buildCat2Detection()
        self._buildMouseAgeDetection()
        return

    def _buildCat1Detection(self):
        """Each vocab is represented as a dict mapping lower case terms to
           their upper case.
        """
        self.cat1TermsDict   = {x.lower() : x.upper() for x in self.cat1Terms}
        self.cat1ExcludeDict = {x.lower() : x.upper() for x in self.cat1Exclude}
        return

    def _gotCat1(self, text):
        """ Return True if text contains a cat1 term not in an exclude context.
        """
        newText, self.cat1Excludes = findMatches(text,
                            self.cat1ExcludeDict, 'excludeCat1', self.numChars)
        newText, self.cat1Matches = findMatches(newText,
                            self.cat1TermsDict, 'cat1', self.numChars)
        return len(self.cat1Matches)

    def _buildCat2Detection(self):
        """Each vocab is represented as a dict mapping lower case terms to
           their upper case.
        """
        self.cat2TermsDict   = {x.lower() : x.upper() for x in self.cat2Terms}
        self.cat2ExcludeDict = {x.lower() : x.upper() for x in self.cat2Exclude}
        return

    def _gotCat2(self, text):
        """ Return True if text contains a cat2 term not in an exclude context.
        """
        newText, self.cat2Excludes = findMatches(text,
                            self.cat2ExcludeDict, 'excludeCat2', self.numChars)
        newText, self.cat2Matches = findMatches(newText,
                            self.cat2TermsDict, 'cat2', self.numChars)
        return len(self.cat2Matches)

    def _buildMouseAgeDetection(self):
        # ageTextTransformer matches age regex's against text
        self.ageTextTransformer = AgeTextTransformer(context=self.ageContext)

        # ageExcludeTextTransformer matches age Exclude terms in the text
        #   around age matches.
        self.ageExcludeTextMapping = TextMappingFromAgeExcludeTerms( \
                'excludeAge', self.ageExclude, lambda x: x.upper(), context=0)

        self.ageExcludeTextTransformer = TextTransformer( \
                                                [self.ageExcludeTextMapping])
            # re to detect strings that would prohibit an age exclude term
            # from causing the exclusion if they occur between
            # the exclude term and the matching age text:
            #   paragraph boundary OR '; '
            #   OR:  '. ' NOT preceded by 'fig' or 'et al' (common abbrevs)
            #   Using (?<!R) "negative look behind".
            #         R has to have a fixed width. So I'm matching 4 chars:
            #         \Wfig = any nonalphnumeric + 'fig'
            #         or 't al'
        regex = PARABOUNDARY_REGEX + r'|[;]\s|(?<!\Wfig|t al)[.]\s'
        self.ageExcludeBlockRE = re.compile(regex)  # ; or . or para

    def _gotMouseAge(self, text):
        """ Return True if we find mouse age terms in text
        """
        newText = self.ageTextTransformer.transformText(text)

        # get ageMatches and throw away "fix" matches
        ageMatches = [ m for m in self.ageTextTransformer.getMatches()
                                        if not m.matchType.startswith('fix')] 
        # check for ageExclude matches
        for m in ageMatches:
            if self._isGoodAgeMatch(m):
                self.ageMatches.append(m)
            else:
                self.ageExcludes.append(m)

        self.ageTextTransformer.resetMatches()
        return len(self.ageMatches)

    def _isGoodAgeMatch(self, m # MatchRcd
                        ):
        """ Return True if m looks like a good mouse age MatchRcd.
            (i.e., no age exclusion terms found in the match or pre/post text)
            If not a good mouse age, return False and:
                Modify m.matchText, m.preText, or m.postText to highlight the
                    exclude term that indicates it is not a good match,
                Set m.matchType to 'excludeAge'
        """
        goodAgeMatch = True     # assume no exclusion terms detected

        # Search m.matchText for age exclusion terms
        newText = self.ageExcludeTextTransformer.transformText(m.matchText)
        excludeMatches = self.ageExcludeTextTransformer.getMatches()

        for em in excludeMatches:       # for exclusion matches in matchText
            newMText = m.matchText[:em.start] + em.replText + \
                                                        m.matchText[em.end:]
            m.matchText = newMText
            goodAgeMatch = False
            break
        self.ageExcludeTextTransformer.resetMatches()

        # Search m.preText for age exclusion terms
        newText = self.ageExcludeTextTransformer.transformText(m.preText)
        excludeMatches = self.ageExcludeTextTransformer.getMatches()

        for em in excludeMatches:       # for exclusion matches in preText
            if not self.hasAgeExcludeBlock(m.preText[em.end:]):
                # no intervening text found that should block the exclude
                newPText = m.preText[:em.start] + em.replText + \
                                                            m.preText[em.end:]
                m.preText = newPText
                goodAgeMatch = False
                break
        self.ageExcludeTextTransformer.resetMatches()

        # Search m.postText for age exclusion terms
        newText = self.ageExcludeTextTransformer.transformText(m.postText)
        excludeMatches = self.ageExcludeTextTransformer.getMatches()

        for em in excludeMatches:      # for exclusion matches in postText
            if not self.hasAgeExcludeBlock(m.postText[:em.start]):
                # no intervening text found that should block the exclude
                newPText = m.postText[:em.start] + em.replText + \
                                                            m.postText[em.end:]
                m.postText = newPText
                goodAgeMatch = False
                break
        self.ageExcludeTextTransformer.resetMatches()

        if not goodAgeMatch:
            m.matchType = 'excludeAge'
        return goodAgeMatch
    
    def hasAgeExcludeBlock(self, text):
        """ Return True/False if text contains ageExclude blocking text
        """
        # this is simpler now that everything is done in the regex
        if self.ageExcludeBlockRE.search(text):
            return True
        else:
            return False

    def routeThisRef(self, text, journal):
        """ Given info about a reference, return "Yes" or "No"
            text is full extracted text, typically w/o references section
            Assumes the text is all lower case.
            Checks journal.
            Searches the full text for cat1 terms.
            Searches figure text for mouse_age and cat2 terms.
        """
        self.cat1Matches = []
        self.cat1Excludes = []
        self.ageMatches = []
        self.ageExcludes = []
        self.cat2Matches = []
        self.cat2Excludes = []

        # uncomment out next line if we are not guarranteed that text is
        #  already all lower case.
        # text = text.lower() # to make things case insensitive

        # for reporting purposes, do all the checks, even though we could
        #   return "No" upon the first failed check

        if journal in self.skipJournals:
            self.goodJournal = 0
        else:
            self.goodJournal = 1

        textLen = len(text)
        gotCat1 = self._gotCat1(text)

        figText = PARABOUNDARY.join(self.figTextConverter.text2FigText(text))
        gotMouseAge = self._gotMouseAge(figText)
        gotCat2     = self._gotCat2(figText)

        if (gotCat1 and gotMouseAge and gotCat2 and self.goodJournal) \
            or textLen < self.minTextLen:
            return 'Yes'
        else:
            return 'No'

    def getExplanation(self):
        """ Return text that summarizes this routing algorithm and vocabs
        """
        output = ''
        output += 'Route refs whose extracted text is < %d chars\n' %  \
                                                    self.minTextLen
        output += 'Category1 terms in full text (%d terms):\n' % \
                                                    len(self.cat1TermsDict)
        for t in sorted(self.cat1TermsDict.keys()):
            output += "\t'%s'\n" % t

        output += 'Category1 Exclude terms (%d terms):\n' % \
                                                    len(self.cat1ExcludeDict)
        for t in sorted(self.cat1ExcludeDict.keys()):
            output += "\t'%s'\n" % t

        output += 'Number of figure text words: %d\n' % self.numFigTextWords

        output += 'Category2 terms in figure text (%d terms):\n' % \
                                                    len(self.cat2TermsDict)
        for t in sorted(self.cat2TermsDict.keys()):
            output += "\t'%s'\n" % t

        output += 'Category2 Exclude terms (%d terms):\n' % \
                                                    len(self.cat2ExcludeDict)
        for t in sorted(self.cat2ExcludeDict.keys()):
            output += "\t'%s'\n" % t

        output += 'Mouse age regular expression - searched in figure text:\n'
        output += self.ageTextTransformer.getBigRegex() + '\n'

        output += 'Num chars around age matches to look for age excludes: %d\n'\
                                                    % self.ageContext
        output += 'Mouse Age Exclude terms (%d terms):\n' % len(self.ageExclude)
        for t in sorted(self.ageExclude):
            output += "\t'%s'\n" % t

        output += 'Mouse age exclude regular expression:\n'
        output += self.ageExcludeTextTransformer.getBigRegex() + '\n'

        output += 'Mouse age exclude blocking regular expression:\n'
        output += self.ageExcludeBlockRE.pattern + '\n'
        output += 'Mouse age exclude blocking logic for ". ":\n'
        output += '". " not following "fig" nor "et al"\n'

        output += 'Route=No for these journals (%d journals):\n' % \
                                                    len(self.skipJournals)
        for t in sorted(self.skipJournals):
            output += "\t'%s'\n" % t

        output += '-' * 50 + '\n'
        return output

    def getGoodJournal(self):  return self.goodJournal
    def getCat1Matches(self):  return self.cat1Matches
    def getCat1Excludes(self): return self.cat1Excludes
    def getAgeMatches(self):   return self.ageMatches
    def getAgeExcludes(self):  return self.ageExcludes
    def getCat2Matches(self):  return self.cat2Matches
    def getCat2Excludes(self): return self.cat2Excludes

    def getPosMatches(self):
        """ Return list of positive matches for most recent article """
        return self.cat1Matches + self.ageMatches + self.cat2Matches

    def getExcludeMatches(self):
        return self.cat1Excludes + self.ageExcludes + self.cat2Excludes

    def getAllMatches(self):
        all = self.cat1Matches + self.cat1Excludes + self.ageMatches + \
                self.ageExcludes + self.cat2Matches + self.cat2Excludes
        return all
# end class GXDrouter -----------------------------------

class AgeTextTransformer (TextTransformer):
    """
    IS a TextTransformer to convert mouse age text to "__mouse_age" with
       specificiable context length - the number of chars to keep around
       each age match.

    To use the age mappings:
      import GXD2aryRouter
      ageTransformer = GXD2aryRouter.AgeTextTransformer()
      newText   = ageTransformer.transformText("some text")
      matches   = ageTransformer.getMatches() # to get MatchRcds for matches
      reportStr = ageTransformer.getReport()  # to get formatted match report
    """
    def __init__(self, context=210, fixContext=10):
        self.context    = context       # n chars around age matches to keep
        self.fixContext = fixContext    # n chars around "fixes" to keep
                                        #   see "fix" age mappings below.
        ageMappings     = getAgeMappings(context=context, fixContext=fixContext)

        super().__init__(ageMappings, reFlags=re.IGNORECASE)

    def getContext(self):    return self.context
    def getFixContext(self): return self.fixContext
#-----------------------------------

def getAgeMappings(context=210, fixContext=10):
    """ Return list of age TextMapping objects with the specified number of
        characters for context to keep for each match.
        fixContext is the num of characters to keep for mappings that just
            fix weird text problems

        These age mappings are a little different from the age mappings
        defined for the autolittriage relevanceClassifier and gxdhtclassifier
        since they are only matched against figure text and have been tuned by
        lots of trial and error for GXD 2ndary triage.
    """
    return [ \
    # Be careful about the order of these mappings.
    # If two can overlap in their matching text, only the first one is applied.

    # Fix mappings: detect weird usages that would erroneously be mapped
    #  to mouse_age
    # by putting these "fix" mappings, 1st, if they match, none of the later
    # mappings will match (1st match wins), even if these don't change the text

    TextMapping('fix2',       # detect figure|table En (En is fig num)
                              # so En is not treated as eday
        r'\b(?:' +
            r'(?:figures?|fig[.s]?|tables?) e\d' +
        r')', lambda x: x,
        context=fixContext),
    TextMapping('fix1',       # correct 'F I G U R E n' so it doesn't
                              # look like embryonic day "E n". "T A B L E" too
        r'\b(?:' +
            spacedOutRegex('figure') +
            r'|' + spacedOutRegex('table') +
        r')\b', lambda x: ''.join(x.split()), # funct to squeeze out spaces
        context=fixContext),

    # The Real age mappings
    TextMapping('dpc',
        # For dpc numbers: allow 0-29 even though most numbers >21 may not be
        #   mice. There tend to not be many matches > 21
        # (0-29 is easy to code as a regexpr: r'(?:\d|[12]\d)' )
        # Allow optional .0 and .5.  regexpr: r'(?:[.][05])?'
        r'\b(?:' +     
            # flavors of "days post conceptus" w/o numbers
            r'd(?:ays?)?(?:\s|-)post(?:\s|-)?' +
                    r'(?:concept(?:ions?|us)?|coit(?:us|um|al)?)' +

            # number 1st, optional space or -, then dpc
            r'|(?:\d|[12]\d)(?:[.][05])?(?:\s|-)?dpc' + 
            r'|(?:\d|[12]\d)(?:[.][05])?(?:\s|-)?d[.]p[.]c' +  # periods

            # dpc 1st, optional space or -, then number
            r'|d[.]?p[.]?c[.]?(?:\s|-)?(?:\d|[12]\d)(?:[.][05])?' +

            # 'd'|'day'|'days' 1st, space or - required, then number, then p.c.
            r'|d(?:ays?)?(?:\s|-)(?:\d|[12]\d)(?:[.][05])?(?:\s|-)?p[.]?c' +
        r')\b', '__mouse_age', context=context),

    TextMapping('eday',
        r'\b(?:' +
            # Acceptable numbers:
            #   any 1 or 2 digs 0-19 w/ .0 .5 .25 .75
            #   any 1 or 2 digs 1-20 w/o decimals.

            # ED|GD, optional space or -, acceptable number
            # ED short for embryonic day, GD short for gestational day
            r'(?:[eg]d(?:\s|-)?' +
               r'(?:(?:1\d|\d)[.][27]5' + # 1-2 digs w/ 2 decimal
                 r'|(?:1\d|\d)[.][05]' +  # 1-2 digs w/ 1 decimal
                 r'|(?:1\d|20|[1-9])' +   # 1-2 digs, no decimals
                 r')(?![.]\d))' +         # not followed by decimal

            # D|day(s), optional space or -, acceptable number, term
            r'|(?:(?:[eg]?d|days?)(?:\s|-)?' +
               r'(?:(?:1\d|\d)[.][27]5' + # 1-2 digs w/ 2 decimal
                 r'|(?:1\d|\d)[.][05]' +  # 1-2 digs w/ 1 decimal
                 r'|(?:1\d|20|[1-9]))' +  # 1-2 digs, no decimals
                 r'(?:\s|-)' +          # ... space or -
                 r'(?:' +               # ... some term
                   r'(?:[a-z]+(?:\s|-))?embryos?' + # (opt word) embryo
                   r'|of(?:\s|-)gestation))' +

            # E, optional space or -, acceptable number
            #     (E1-3 are rarely used & often mean other things)
            #     (we allow E14 here since typically in figure text, it will
            #      be an age, not a cell line. In gxdhtclassifier, we omit E14)
            r'|(?:(?<![-])(?:' + # not preceded by '-'
                                  # (if preceded by '-', often "-En" is part of
                                  #  a symbol or cell line. If En-En is truly
                                  #  an age range, the 1st age will match)
               r'e(?:\s|-)?(?:1\d|\d)[.][27]5' +  # 1-2 digs w/ 2 decimal
               r'|e(?:\s|-)?(?:1\d|\d)[.][05]' +  # 1-2 digs w/ 1 decimal
               r'|e(?:\s|-)?(?:1\d|20|[4-9]))' +  # 1-2 digs, no decimals
               r'(?![.]\d|[%]|(?:(?:\s|-)(?:bp|ml|mg)\b)))' + # not followed by
                                               # decimal or % -bp -ml -mg

            # Embryonic/gestational term, space or -, acceptable number
            r'|(?:' +
               r'(?:(?:gestation(?:al)?|embryo(?:nic)?)(?:\s|-)days?' +
                 r'|embryonic)' +
               r'(?:\s|-)?' +  # optional space or -
               # number
               r'(?:1\d[.][27]5|\d[.][27]5' + # 1-2 digs w/ 2 decimals
               r'|1\d[.][05]|\d[.][05]' +     # 1-2 digs w/ 1 decimal
               r'|20|1\d|[1-9]))' +           # 1-2 digs, no decimals

            # Number 1st, optional space or -, then some "day/embryo" term
            r'|(?:(?:1\d[.][27]5|\d[.][27]5' + # 1-2 digs w/ 2 decimals
                r'|1\d[.][05]|\d[.][05]' +     # 1-2 digs w/ 1 decimal
                r'|20|1\d|[1-9])' +            # 1-2 digs, no decimals
               # num followed by...
               r'(?:\s|-)?' +          # optional space or -
               r'(?:' +
                 r'(?:' +         # d|day, optional "old", ...some term...
                   r'(?:d|days?)(?:\s|-)(?:old(?:\s|-))?' + # d|day, opt'l old
                   r'(?:embryos?|gestation))' +
                 r'|(?:' +        # d|day, optional "old", mice + dev_term
                   r'(?:d|days?)(?:\s|-)(?:old(?:\s|-))?' + # d|day, opt'l old
                   r'(?:(?:mice|mouse)(?:\s|-)' +
                     r'(?:embryos?|fetus(?:es)?|fetal|zygotes?' +
                      r'|blastocysts?|morulae?)' +
                   r'))' +
                 r'|(?:' +        # days after fertilization
                   r'days?(?:\s|-)(?:post|after)(?:\s|-)' +
                   r'(?:fertilization|gestation))' +
                 r'|(?:' +        # ed|gd|gestational day
                   r'(?:ed|gd|(?:embryonic|gestational)(?:\s|-)days?))))' +

            # Odd special case to match "17.E mouse" that appears in MGI:6512808
            # not sure this is worth it.
            r'|(?:(?:20|1\d|[1-9])[.]e(?:\s|-)mouse)' +  # 1-2 digs w/o decimals

            # final catch all
            r'|embryonic(?:\s|-)days?' + # spelled out, don't worry about nums
        r')\b', '__mouse_age', context=context),

    TextMapping('ts',
        r'\b(?:' +
            r'theiler\sstages?' +
            r'|TS(?:\s|-)?[7-9]' +  # 1 digit, 0-6 not used or are other things
            r'|TS(?:\s|-)?[12]\d' +   # 2 digits
        r')\b', '__mouse_age', context=context),
    TextMapping('ee',   # early embryo terms
                        # mesenchymal mesenchymes? ?
        r'\b(?:' +
            r'blastocysts?|blastomeres?|headfold|autopods?' +
                        # embryo(nic) <opt word> lysates|extracts
            r'|embryo(?:nic)?(?:\s|-)(?:[a-z]+(?:\s|-))?(?:lysates?|extracts?)'+
            r'|(?:(?:early|mid|late)(?:\s|-))?streak|morulae?|somites?' +
            r'|(?:limb(?:\s|-)?)buds?' +    # bud w/ limb in front
            r'|(?<!fin(?:\s|-))buds?' +     # bud w/o 'fin ' in front
            r'|(?:' +
                r'(?:[1248]|one|two|four|eight)(?:\s|-)cells?(?:\s|-)' +
                r'(?:' +   # "embryo" or "stage" must come after [1248] cell
                    r'stages?|' +
                    r'(?:' +
                        r'(?:(?:mouse|mice|cloned)(?:\s|-))?embryos?' +
                    r')' +
                r')' +
            r')' +
        r')\b', '__mouse_age', context=context),
    TextMapping('developmental',   # "developmental" terms
        r'\b(?:' +  # Do we want to add simply "embryos?"
            r'zygotes?' +
            r'|(?:mice|mouse)(?:\s|-)embryos?' +        # more general
            r'|development(?:al)?(?:\s|-)(?:(?:mice|mouse)(?:\s|-))?stages?' +
            r'|development(?:al)?(?:\s|-)(?:(?:mice|mouse)(?:\s|-))?ages?' +
            r'|embryo(?:nic)?(?:\s|-)(?:(?:mice|mouse)(?:\s|-))?stages?' +
            r'|embryo(?:nic)?(?:\s|-)(?:(?:mice|mouse)(?:\s|-))?ages?' +
            r'|embryo(?:nic)?(?:\s|-)development' +
            r'|(?:st)?ages?(?:\s|-)of(?:\s|-)?embryos?' +
            r'|development(?:al)?(?:\s|-)time(?:\s|-)(?:series|courses?)' +
        r')\b', '__mouse_age', context=context),
    TextMapping('fetus',   # fetus terms
        r'\b(?:' +
            r'fetus|fetuses' +
            r'|(?:fetal|foetal)(?!\s+(?:bovine|calf)\s+serum)' +
        r')\b', '__mouse_age', context=context),
    TextMapping('misc',   # misc terms
        r'\b(?:' +
            r'genepaint' +
            r'|embryo(?:\s|-)mouse(?:\s|-)brain' +
        r')\b', '__mouse_age', context=context),
    ]
# end getAgeMappings() -----------------------------------

class TextMappingFromAgeExcludeTerms (TextMappingFromStrings):
    """
    Is a: TextMapping for matching age exclusion terms
    Does: converts ageExclude vocab terms (a list of strings) to regex's with
            ' ' converted to r'\s' (any whitespace)
            '_' converted to r'\b' (word boundary)
            '#' converted to r'\d' (any digit)
          This gives the curators to a way to make simple regex's from vocab
          terms.
    """

    def _str2regex(self, s):
        """ Return re.escape(s) string with
            '_' replaced w/ word boundaries (r'\b')
            ' ' replaced with r'\s' to match any whitespace
            '#' replaced with r'\d' to match any digit
        """
        regex = re.escape(s)
        regex = regex.replace(' ', 's')   # escape puts '\' before ' ' 
        regex = regex.replace('#', 'd')   # escape puts '\' before '#' 
        regex = regex.replace('_', r'\b') # escape does not put '\' before '_' 
        return regex
#-----------------------------------

def findMatches(text, termDict, matchType, ctxLen):
    """ find all matches in text for terms in the termDict:
            {'term': 'replacement text for the term'}.
        Return the modified text and list of MatchRcds for all the matches.
        In addition to the term replacements, the modified text has all
            '\n' replaced by ' '.
        Note: the order that the terms are matched against the text is random,
        so if some terms are substrings of other terms, which one matches
        first is undefined.
    """
    resultText = text           # resulting text if termDict is empty

    findText = text.replace('\n', ' ')  # So we can match terms across lines
                                        # This is the text to search in.

    matchRcds = []                      # the matches to return

    textLen = len(text)

    for term, replacement in termDict.items():
        termLen = len(term)
        resultText = ''      # modified text from this term's transformations

        # find all matches to the term
        start = 0   # where to start the search from
        matchStart = findText.find(term, start)
        matchEnd = 0
        while matchStart != -1:     # got a match
            matchEnd = matchStart + termLen
            matchText = text[matchStart : matchEnd]

            preStart = max(0, matchStart-ctxLen)
            postEnd  = min(textLen, matchEnd + ctxLen)
            pre  = text[preStart : matchStart]
            post = text[matchEnd : postEnd]

            m = MatchRcd(matchType, matchStart, matchEnd, matchText,
                                                pre, post, replacement)
            matchRcds.append(m)

            resultText += findText[start : matchStart] + replacement

            # find next match
            start = matchEnd
            matchStart = findText.find(term, start)

        resultText += findText[matchEnd:]    # text after last match
        findText = resultText         # for next term, search the modified text

    return resultText, matchRcds
# end findMatches() -----------------------------------
