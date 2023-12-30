import cv2
import csv
import json
import os
import shutil
import pandas
print("Before importing spacy")
import spacy
print("Imported spacy")


excelMetadata = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\metadata\papersMetadata.xlsx"
rawOCRFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\rawTexts"
manuallyCorrectedTextFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\manualCleanText"
reportPath=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\evalQualitéOCR.tsv"

def extractRealWordNumbers(doc):
    #extrait d'un doc processé par spacy un dictionnaire avec une entrée par mot réel (commençant par lettre ou chiffre)
    #où la valeur sera le nombre d'occurrences
    d={}
    for t in doc:
        if t.text[0].isalnum():
            if t.text in d:
                d[t.text]+=1
            else:
                d[t.text]=1
    return d
            
def spacyDocFromPath(sPath):
    fText=open(sPath,"r",encoding="utf-8")
    sText=fText.read()
    fText.close()
    return nlp(sText)


df = pandas.read_excel(excelMetadata)
necroCol=-1
idCol=-1
for i in range(0,len(df.columns)):
    if df.columns[i]=="Nécrologie": necroCol=i
    if df.columns[i]=="PDF": idCol=i
metadataList = df.values.tolist()
listNecros=[]
for row in metadataList:
    if isinstance(row[necroCol],str) and row[necroCol].startswith("N"):
        s=row[idCol]
        bulletinID=s.split("_")[0]
        articleWithinBulletinID=s.split("_")[-1].split(".")[0]
        if len(articleWithinBulletinID)<=2:       #exclude manually split ones like 13A, 13B
            listNecros.append(bulletinID+"_"+articleWithinBulletinID)

#initialise Spacy
nlp = spacy.load('fr_core_news_sm', exclude=['parser', 'ner'])
french_tagger_pipeline = spacy.load('fr_single_upos2usas_contextual')
nlp.add_pipe('pymusas_rule_based_tagger', source=french_tagger_pipeline)

f=open(reportPath,"w",encoding="utf-8")
f.write(f'Article\tTokens\tErreurs\n')
for n in listNecros:
    print("Processing "+n)
    bulletinID=n.split("_")[0]
    articleWithinBulletinID=n.split("_")[1]
    rawOCRPath=os.path.join(rawOCRFolder,bulletinID+"_art_"+articleWithinBulletinID+".pdf_main.txt")
    cleanTextPath=os.path.join(manuallyCorrectedTextFolder,bulletinID+"_"+articleWithinBulletinID+"_main.txt")
    if not(os.path.exists(rawOCRPath)): print(rawOCRPath)
    if not(os.path.exists(cleanTextPath)): print(cleanTextPath)
    dNumbersOCR=extractRealWordNumbers(spacyDocFromPath(rawOCRPath))
    dNumbersClean=extractRealWordNumbers(spacyDocFromPath(cleanTextPath))
    #On calcule donc le nombre de tokens, et on évalue le nombre d'erreurs via la différence
    nTotal=0
    nErrors=0
    for k in dNumbersClean:
        nTotal+=dNumbersClean[k]
        nThisWordInOCR=0
        if k in dNumbersOCR: nThisWordInOCR=dNumbersOCR[k]
        nErrors+=abs(dNumbersClean[k]-nThisWordInOCR)
    f.write(f'{bulletinID}_{articleWithinBulletinID}\t{nTotal}\t{nErrors}\n')

f.close()
