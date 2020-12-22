#
# Example command to get refs that need relevance prediction from db and into
#  a sample file
getRefsToPredict.py -s mgi-testdb4 -d scrumdog   > samplefile

# Example command to run predictions on that sample file and create prediction
#  file
predict.py -m relevanceClassifier.pkl -p figureTextLegCloseWords50 -p removeURLsCleanStem samplefile > predictions
