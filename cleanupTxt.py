import os
import json
from lxml import etree as et
from nltk.tokenize import WordPunctTokenizer

DELADictionaryPath=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Code\resources\dela-fr-public-u8.dic.xml"
dictCache=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Code\resources\dela-fr-public-u8.dic.json"
#inputFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\rawTxt"
#outputFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Nécrologies\cleanTxt"
inputFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\rawTexts"
outputFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\textsAutoProcessed"

def loadDELADict(dictPath,dictCache):
    if os.path.exists(dictCache):
        f=open(dictCache,"r")
        l = json.load(f)
        f.close()
        print("Dictionary was in cache")
    else:
        print("Starting to load dict")
        l=[]
        frenchDict=open(DELADictionaryPath,"br")
        etree=et.parse(frenchDict).getroot()
        formList=etree.xpath("//form")
        i=0
        for f in formList:
            #if not(f.text in l):
            #   l.append(f.text)
            #    i=i+1
            l.append(f.text)
            i=i+1
            if i%1000==0:
                print(i)
        frenchDict.close
        print("Finished loading dict")
        with open(dictCache,"w") as f:
            json.dump(l,f)
    return l

def cleanUp(s,frenchDict):
    #nettoie un texte :
    #supprime les \n (line feed) inutiles
    #remplace les \n\n (changements de paragraphe) par un @PARAGRAPH
    #remplace les \n par un espace
    #tente de régler le problème des tirets en fin de ligne
    #remplace les espaces multiples par des espaces simples
    #---------------------------------------------------------
    #Tout d'abord, on remplace les n>=3 linefeeds par 2 linefeeds
    while s.find("\n\n\n")>0:
        s=s.replace("\n\n\n","\n\n")
    #Ensuite, on essaie de voir si 2 linefeeds successifs représentent un changement de paragraphe
    #ou une erreur d'OCR. On considère que si la ligne précédente se termine par un point, c'est un paragraphe
    l = s.split("\n\n")
    s=""
    for i in range(0,len(l)-1):
        s+=l[i].strip()
        if l[i].rstrip().endswith("."):
            s+=" @PARAGRAPH "
        else:
            s+=" \n "
    s+=l[len(l)-1].strip()
    #Ensuite, on remplace les \n en faisant attention à l'hyphénation
    l = s.split("\n")
    s=""
    for i in range(0,len(l)-1):
        s+=l[i].strip()
        if l[i].rstrip().endswith("-"):
            #gestion des traits d'union
            #on cherche le dernier "token" de la ligne précédente, et le premier "token" de la prochaine ligne
            to = WordPunctTokenizer()
            prevTokenized=to.tokenize(l[i].strip())
            lastToken="ZZZZNOTZZZZ"
            if len(prevTokenized)>=2:
                lastToken=prevTokenized[-2].lower()  #le dernier token est le "-", on prend donc l'avant dernier [-2]
            nextTokenized=to.tokenize(l[i+1].strip())
            firstToken="ZZZZNOTZZZZ"
            if len(nextTokenized)>=1:
                firstToken=nextTokenized[0].lower()
            #print("Last and first tokens are {} and {}".format(lastToken,firstToken))
            if lastToken+firstToken in frenchDict:
                s=s[0:-1]
                #print("Merging")
            else:
                pass
                #print("Not merging")
        else:
            s+=" "
    s+=l[len(l)-1].strip()
    #enfin, on supprime les espaces multiples
    while s.find("  ")>0:
        s=s.replace("  "," ")
    #on corrige les erreurs d'ocr fréquentes
    lOCRfixes=[(" ct "," et "), (" 1l ", " il ")]
    for fix in lOCRfixes:
        s=s.replace(fix[0],fix[1])
    return s

frenchDict = loadDELADict(DELADictionaryPath,dictCache)
for f in os.listdir(inputFolder):
    if f.lower().endswith(".txt"):
        fText=open(os.path.join(inputFolder,f),"r",encoding="utf-8")
        sText=fText.read()
        fText.close()
        sCleanText=cleanUp(sText,frenchDict)
        sOutPath=os.path.join(outputFolder,f)
        fText=open(sOutPath,"w",encoding="utf-8")
        fText.write(sCleanText)
        fText.close()
        print("{}:{} - {}".format(f,len(sText),len(sCleanText)))


