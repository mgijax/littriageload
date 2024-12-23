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
pdfFile = '1s20S2589004221005058main.pdf'
pdf = PdfParser.PdfParser(os.path.join(pdfPath, pdfFile))
pdftext = pdf.getText();
logFile.write(pdftext)

#textSplitter = extractedTextSplitter.ExtTextSplitter()
#(bodyText, refText, figureText, starMethodText, suppText)  = textSplitter.splitSections(pdftext)
#logFile.write(bodyText, refText, figureText, starMethodText, suppText)

logFile.close()

