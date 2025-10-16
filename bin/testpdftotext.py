#
# use this to test the:
#   pdf parser
#
# usage:  
# edit pdfFile = '1s20S2589004221005058main.pdf'
# $PYTHON testpdftotext.py
# will send output to textpdftotext.log
#

import sys 
import os
import PdfParser
import extractedTextSplitter

PdfParser.setLitParserDir(os.getenv('MGIUTILS') + '/litparser')

os.system('rm -rf textpdftotext.log')
logFile = open('textpdftotext.log', 'w')

pdfPath = os.getenv('DATALOADSOUTPUT') + '/mgi/littriageload/input.last/' + 'smb'
pdfFile = 'MID_40446798.pdf'
pdf = PdfParser.PdfParser(os.path.join(pdfPath, pdfFile))
pdftext = pdf.getText();
logFile.write(pdftext)
doiid = pdf.getFirstDoiID()
logFile.write(doiid + "\n")

#textSplitter = extractedTextSplitter.ExtTextSplitter()
#(bodyText, refText, figureText, starMethodText, suppText)  = textSplitter.splitSections(pdftext)
#logFile.write('bodyTest:%s\n' % bodyText)
#logFile.write('###\nrefText:%s\n' % refText)
#logFile.write('###\nfigureText:%s\n' % figureText)
#logFile.write('###\nstartText:%s\n' % starMethodText)
#logFile.write('###\nsuppText:%s\n' % suppText)

logFile.close()

