import csv
import os
import requests
import json

resultsfolder=r'E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\intermediate'
infileJSON=os.path.join(resultsfolder,"bifao_papers.json")
allArticles=json.load(open(infileJSON,encoding="utf-8"))
for ar in allArticles:
    url=ar["url"]
    destFilePath=os.path.join(resultsfolder,ar["nom_fichier"])
    if not(os.path.exists(destFilePath)):
        print("Start downloading "+ url)
        try:
            r=requests.get(url,allow_redirects=True,timeout=15)
            open(destFilePath,"wb").write(r.content)
            print("Finished downloading "+ url)
        except requests.exceptions.Timeout:
            print("Error downloading " + url)
        
