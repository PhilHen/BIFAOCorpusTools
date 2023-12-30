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
textsFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\textsAutoProcessed"
necrologiesTextFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\manualCleanText"
jsonOutputFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\spacyJsons"
reportPath=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\powerReport.txt"

def spacyDocFromPath(sPath):
    fText=open(sPath,"r",encoding="utf-8")
    sText=fText.read()
    fText.close()
    return nlp(sText)

def serializeSpacyDoc(doc):
    return [{'text': t.text, 'lemma': t.lemma_, 'pos': t.pos_, 'pymusas_tags': t._.pymusas_tags} for t in doc]

df = pandas.read_excel(excelMetadata)
necroCol=-1
idCol=-1
idLang=-1
for i in range(0,len(df.columns)):
    if df.columns[i]=="Nécrologie": necroCol=i
    if df.columns[i]=="PDF": idCol=i
    if df.columns[i]=="Langue": idLang=i
metadataList = df.values.tolist()

#initialise Spacy
nlp = spacy.load('fr_core_news_sm', exclude=['parser', 'ner'])
french_tagger_pipeline = spacy.load('fr_single_upos2usas_contextual')
nlp.add_pipe('pymusas_rule_based_tagger', source=french_tagger_pipeline)

f=open(reportPath,"w",encoding="utf-8")
f.write(f'Article\tTokens\tPouvoir\n')

for row in metadataList:
    if row[idLang]=="F":
        isNecro= isinstance(row[necroCol],str) and row[necroCol].startswith("N")
        s=row[idCol]
        print(s)
        bulletinID=s.split("_")[0]
        articleWithinBulletinID=s.split("_")[-1].split(".")[0]
        #les nécrologies ont été nettoyées à la main -> on va chercher, dans ce cas, dans un répertoire spécifique (avec un nom de fichier différent)
        if isNecro:
            textPath=os.path.join(necrologiesTextFolder,bulletinID+"_"+articleWithinBulletinID+"_main.txt")
        else:
            textPath=os.path.join(textsFolder,bulletinID+"_art_"+articleWithinBulletinID+".pdf_main.txt")
        if not(os.path.exists(textPath)): print(textPath)
        l=serializeSpacyDoc(spacyDocFromPath(textPath))
        lPower=[t for t in l if "S7.1" in t["pymusas_tags"][0]]
        outfileJSON=os.path.join(jsonOutputFolder,s+".json")
        with open(outfileJSON,"w") as fjson:
            json.dump(l,fjson)
            fjson.close()
        outfileJSONPower=os.path.join(jsonOutputFolder,s+"_power.json")
        with open(outfileJSONPower,"w") as fjson:
            json.dump(lPower,fjson)
            fjson.close()            
        f.write(f'{s}\t{len(l)}\t{len(lPower)}\n')
f.close()
