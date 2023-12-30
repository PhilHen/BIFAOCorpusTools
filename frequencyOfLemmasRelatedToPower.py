#Ce script python calcule, dans les 58 articles marqués "Pouvoir" dans l'excel de métadonnées
# la fréquence des lemmes liés au pouvoir selon le tag sémantique MUSAS
# On suppose que les résultats de la lemmatisation/tagging MUSAS est déjà sauvé dans des fichiers json

import json
import unicodedata
from lxml import etree
from lxml.builder import E
import cv2
import csv
import os
import shutil
import pandas
print("Before importing spacy")
import spacy
print("Imported spacy")


excelMetadata = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\metadata\papersMetadata.xlsx"
textsFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\textsAutoProcessed"
necrologiesTextFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\manualCleanText"
jsonFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\spacyJsons"
reportPath=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\powerLemmaReport.txt"

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
powerCol = -1
for i in range(0,len(df.columns)):
    if df.columns[i]=="Nécrologie": necroCol=i
    if df.columns[i]=="PDF": idCol=i
    if df.columns[i]=="Pouvoir": powerCol=i
metadataList = df.values.tolist()

#initialise Spacy
nlp = spacy.load('fr_core_news_sm', exclude=['parser', 'ner'])
french_tagger_pipeline = spacy.load('fr_single_upos2usas_contextual')
nlp.add_pipe('pymusas_rule_based_tagger', source=french_tagger_pipeline)

dLemmasOfPower={}
for row in metadataList:
    if isinstance(row[powerCol],str) and row[powerCol].startswith("P"):            #critère de sélection du corpus pouvoir
        isNecro= isinstance(row[necroCol],str) and row[necroCol].startswith("N")
        s=row[idCol]
        print(s)
        bulletinID=s.split("_")[0]
        articleWithinBulletinID=s.split("_")[-1].split(".")[0]
        #les nécrologies ont été nettoyées à la main -> on va chercher, dans ce cas, dans un répertoire spécifique (avec un nom de fichier différent)
        shortId=bulletinID+"_"+articleWithinBulletinID
        if isNecro:
            textPath=os.path.join(necrologiesTextFolder,bulletinID+"_"+articleWithinBulletinID+"_main.txt")
        else:
            textPath=os.path.join(textsFolder,bulletinID+"_art_"+articleWithinBulletinID+".pdf_main.txt")
        spacyJsonPath=os.path.join(jsonFolder,s+".json")
        if os.path.exists(spacyJsonPath):
            ftemp=open(spacyJsonPath,"r")
            l = json.load(ftemp)
            ftemp.close()
        else:
            l=serializeSpacyDoc(spacyDocFromPath(textPath))
        for t in l:
            if "S7.1" in t["pymusas_tags"][0]:
                if not(t["lemma"] in dLemmasOfPower):
                       dLemmasOfPower[t["lemma"]]=0
                dLemmasOfPower[t["lemma"]]+=1

f=open(reportPath,"w",encoding="utf-8")
f.write(f'Lemme\tn\n')
for k in dLemmasOfPower:
    f.write(f'{k}\t{dLemmasOfPower[k]}\n')
f.close()
