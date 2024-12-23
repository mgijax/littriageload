#
# use this to test the:
#   pubmed agent 
#   directly to the eutils/api
#
# usage:  
# edit pubmedids as needed
# $PYTHON testeutilsapi.py
#

import sys 
import os
import db
import Pdfpath
import extractedTextSplitter

db.setTrace()

pdf = PdfParser.PdfParser(os.getenv('DATALOADSOUTPUT') + '/input.last/??', pdfFile))
pdftext = pdf.getText();
print(pdftext)
textSplitter = extractedTextSplitter.ExtTextSplitter()

#(bodyText, refText, figureText, starMethodText, suppText)  = textSplitter.splitSections(pdftext)
#print(bodyText, refText, figureText, starMethodText, suppText)

