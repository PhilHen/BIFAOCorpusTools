from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import csv
import os
import json

driver=webdriver.Chrome()
columnHeads=["auteur","titre","pages","taille","nom_fichier"]
resultsfolder=r'E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\intermediate'
outfileCSV=os.path.join(resultsfolder,"bifao_papers.csv")
outfileJSON=os.path.join(resultsfolder,"bifao_papers.json")
allArticles=[]
for i in range(1, 124):
 contents_table_url="https://www.ifao.egnet.net/bifao/"+str(i)
 driver.get(contents_table_url)
 articles = driver.find_elements(By.XPATH,"//table/tbody/tr")
 #maintenant, vérifions lesquels possèdent exactement 5 colonnes, dont la dernière se termine par ".pdf"
 #ce seront là les articles
 for a in articles:
     cols=a.find_elements(By.XPATH,"td")
     if len(cols)==5 and cols[4].text.endswith(".pdf"):
         d=dict(zip(columnHeads,[c.text for c in cols]))
         d["url"]=cols[4].find_elements(By.XPATH,"a")[0].get_attribute("href")
         d["year"]=1900+i
         allArticles.append(d)
         
with open(outfileCSV,'w',newline='',encoding='utf-8') as f:
    csv.writer(f,delimiter="\t").writerows([ar.values() for ar in allArticles])
with open(outfileJSON,"w") as f:
    json.dump(allArticles,f)

    
