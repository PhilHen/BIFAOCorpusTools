import cv2
import csv
import json
import os
import shutil
import pandas


excelMetadata = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\bifao_papers_with_language.xlsx"
rootDir= r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate"
sourceTextsFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\texts"
sourcePDFFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate"
pathListNecros = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\listeNécros.txt"
destPDFFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\pdf"
destTextsFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\rawtxt"
jsonFile = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\bifao_papers.json"

def getArticle(articles,key,value):
    for a in articles:
        if a[key]==value: return a

metadataList = pandas.read_excel(excelMetadata).values.tolist()

def getMetadataItem(metadataList,pdfFileName,index):    #1 est la langue, 2 est un flag indiquant si c'est une nécrologie, 3 est le nom court
    for i in metadataList:
        if i[7]==pdfFileName: return  i[index]
        


f=open(jsonFile,"r")
articles = json.load(f)
f.close()

#on a préparé à la main un fichier texte avec les noms de fichier des nécrologies
with open(pathListNecros) as f:
    data=f.read().split("\n")
for d in data:
    a=getArticle(articles,"nom_fichier",d)
    if a:
        titre=a["titre"]
        auteur =a["auteur"].replace(" ","").replace("-","").replace(",","@")
        articleCode=str(a["year"])+"@"+d.split("_")[2].split(".")[0]
        shortSubject = getMetadataItem(metadataList,d,3)
        shortName=shortSubject+"_"+str(a["year"])+"_"+articleCode+"_"+auteur
        sSourcePDFPath=os.path.join(sourcePDFFolder,d)
        sDestPDFPath=os.path.join(destPDFFolder,d)
        if os.path.exists(sSourcePDFPath) and not(os.path.exists(sDestPDFPath)):
            shutil.copyfile(sSourcePDFPath,sDestPDFPath)
        for ext in ["main","footnotes"]:    #["main","footnotes"]
            sSourceTextPath=os.path.join(sourceTextsFolder,d+"_"+ext+".txt")
            #retrouve les métadonnées de l'article
            sDestTextPath=os.path.join(destTextsFolder,shortName+".txt")
            if os.path.exists(sSourceTextPath) and not(os.path.exists(sDestTextPath)):
                shutil.copyfile(sSourceTextPath,sDestTextPath)
