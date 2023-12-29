import json
import os


rootDir= r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate"
sourceTextsFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\texts"
destTextsFolder = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\textsGroupedByYear"
jsonFile = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\bifao_papers.json"

def getArticle(articles,key,value):
    for a in articles:
        if a[key]==value: return a

textsByYear={}
f=open(jsonFile,"r")
articles = json.load(f)
f.close()

for a in articles:
    sArticleID = a["nom_fichier"].split("_")[0] + "_" + a["nom_fichier"].split("_")[2].split(".")[0]
    print(sArticleID)
    mainArticleTextPath=os.path.join(sourceTextsFolder,a["nom_fichier"]+"_main.txt")
    f=open(mainArticleTextPath,encoding="utf-8")
    articleText=f.read()
    f.close()
    if a["year"] in textsByYear:
        textsByYear[a["year"]]+="------------------------\n"*3
    else:
        textsByYear[a["year"]]=""
    textsByYear[a["year"]]+="@ARTICLE_"+sArticleID+"_START\n"+articleText
for k in textsByYear:
    yearTextPath=os.path.join(destTextsFolder,str(k)+".txt")
    f=open(yearTextPath,"w",encoding="utf-8")
    f.write(textsByYear[k])
    f.close()
stop

