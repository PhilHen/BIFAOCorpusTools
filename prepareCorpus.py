#Ce script python crée les fichiers d'un corpus (avec méta-données) au format TEI-XML ou Hyperbase10 dans le répertoire de sortie
#Il se base sur un Excel contenant les métadonnées et des json (un par fichier texte) contenant la tokenisation / lemmatisation / annotation sémantique réalisée par Spacy

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
corpusOutputFolder=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Corpuses\FullTest"
corpusOutputHyperbase10Path=r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Corpuses\FullTest.txt"
blOutputTEI = True
blOutputHyperbase10Individual = False              #pour les petits corpus, on utilise Individual
blOutputHyperbase10GroupedByBulletin = True          #pour les petits corpus, on utilise GroupedByBulletin - les 2 sont incompatibles

def generateXmlForText(docTitle,sourceURL,docId,lSpacy,dMetadata,sFootnotes,isNecro):
    #generates the root element
    #lSpacy doit etre une liste de tokens traités par Spacy-MUSAS du type {'text': 'la', 'lemma': 'le', 'pos': 'DET', 'pymusas_tags': ['Z5']}
    #----------------------
    #tout d'abord, on traite les footnotes pour pouvoir préparer les renvois.
    #Certaines de ces footnotes ne sont pas lié à un renvoi dans le texte (elles seront placées à la fin du texte)
    #D'autres sont liées à un renvoi dans le texte
    dictFootnotes={}    #dictionnaire de listes de "tokens" (ici, on sépare simplement par l'espace car le but est de détecter nos tags spécifiques, toujours indiqués par des espaces, non de tokeniser)
    curContext="NONE"
    for ft in sFootnotes.split(" "):
        if ft.startswith("@REF_") and ft.split("_")[3]=="NOTESTART":
            curContext=ft.split("_")[4]
        elif not(ft.startswith("@")):
            if not(curContext) in dictFootnotes: dictFootnotes[curContext]=[]
            dictFootnotes[curContext].append(ft)
    #----------------------------------
    #Fin du processing des footnotes, on génère à présent le xml
    #----------------------------------
    URL_PYMUSAS_REFERENCE = "https://ucrel.github.io/pymusas/usage/how_to/tag_text#french"
    URL_SPACY_REFERENCE = "https://spacy.io/"
    URL_SOURCE_DOCUMENTS="(BIFAO en ligne) processed using python scripts in https://github.com/PhilHen/BIFAOCorpusTools (typographical zones detected using OpenCV, OCR with Tesseract)"

    EDITORIALDECL_CORRECTION="Les erreurs d'orthographe confirmées par examen du PDF source n'ont pas été corrigées."
    if isNecro: EDITORIALDECL_CORRECTION+=" Une vérification et correction manuelle du texte a été réalisée par Ph. Hennebert " + \
                                               "(philippe.hennebert@student.uliege.be) le 29/12/2023"
    EDITORIALDECL_HYPHENATION="Les mots coupés en fin de ligne ont été réassemblés automatiquement, pour autant que la forme combinée sans trait d'union " + \
                                   "soit attestée dans le dictionnaire français https://unitexgramlab.org/fr/language-resources"
    PUBLICATIONSTMT="Corpus produit par l'étudiant MA1 Ph. Hennebert (philippe.hennebert@student.uliege.be) du cours de l'Université de Liège Corpus INFO0943: " + \
                                    "'Corpus textuels: principes de constitution et d'analyse'"
    
    root=etree.Element("TEI",nsmap={None:"http://www.tei-c.org/ns/1.0"})
    EFileDesc=E.fileDesc(E.titleStmt(E.title(docTitle)),E.publicationStmt(PUBLICATIONSTMT),E.sourceDesc(E.p(sourceURL+" "+URL_SOURCE_DOCUMENTS)))
    ETaxPos=E.taxonomy(E.bibl(E.title("pos tagset build from " +URL_SPACY_REFERENCE)),id="frpos")
    ETaxLemma=E.taxonomy(E.bibl(E.title("fr lemma of the model " +URL_SPACY_REFERENCE)),id="frlemma")
    ETaxSemantic=E.taxonomy(E.bibl(E.title("semantic tagging " +URL_PYMUSAS_REFERENCE)),id="frMUSAS")
    EEncodingDesc=E.encodingDesc(E.classDecl(ETaxPos,ETaxLemma,ETaxSemantic),E.editorialDecl(E.correction(EDITORIALDECL_CORRECTION),E.hyphenation(EDITORIALDECL_HYPHENATION)))
    ETeiHeader=E.teiHeader(EFileDesc,EEncodingDesc)
    EText=E.text(id=docId)
    Ep=E.p("")
    for md in dMetadata:
        EText.set(md,dMetadata[md])
    j=0
    for w in lSpacy:
        if not(w["text"].startswith("@")):
            Ep.append(E.w(w["text"],frlemma=w["lemma"],frpos=w["pos"],frMUSAS=w["pymusas_tags"][0]))
        elif w["text"]=="@PARAGRAPH":
            EText.append(Ep)
            Ep=E.p("")
        elif w["text"].startswith("@ARTICLE") and w["text"].split("_")[3]=="PAGE":
            Ep.append(E.pb(n=w["text"].split("_")[4]))
        elif w["text"].startswith("@REF_") and w["text"].split("_")[3]=="NOTECALL":
            noteNumber=w["text"].split("_")[4]
            if noteNumber in dictFootnotes:
                Ep.append(E.note(" ".join(dictFootnotes[noteNumber]),n=noteNumber,place="bottom"))
    #on met tout à la fin les notes qu'on n'a pas pu attacher dans le texte
    if "NONE" in dictFootnotes:
        Ep.append(E.note(" ".join(dictFootnotes["NONE"]),place="bottom"))
    EText.append(Ep)
    root.append(ETeiHeader)
    root.append(EText)
    return root

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
langCol=-1
titleCol=-1
authorCol=-1
powerCol = -1
yearCol = -1
deceasedNameCol = -1
deceasedJobCol=-1
for i in range(0,len(df.columns)):
    if df.columns[i]=="Nécrologie": necroCol=i
    if df.columns[i]=="PDF": idCol=i
    if df.columns[i]=="Langue": langCol=i
    if df.columns[i]=="Titre": titleCol=i
    if df.columns[i]=="Auteur": authorCol=i
    if df.columns[i]=="Pouvoir": powerCol=i
    if df.columns[i]=="Année": yearCol=i
    if df.columns[i]=="NomDéfunt": deceasedNameCol=i
    if df.columns[i]=="MétierDéfunt": deceasedJobCol=i
metadataList = df.values.tolist()

#initialise Spacy
nlp = spacy.load('fr_core_news_sm', exclude=['parser', 'ner'])
french_tagger_pipeline = spacy.load('fr_single_upos2usas_contextual')
nlp.add_pipe('pymusas_rule_based_tagger', source=french_tagger_pipeline)

if blOutputHyperbase10GroupedByBulletin:
    dByBulletin={}
sHyperbase10Output="\n\n"
for row in metadataList:
    #if row[langCol]=="F" and isinstance(row[necroCol],str) and row[necroCol].startswith("N"):            #critère de sélection du corpus néro
    #if row[langCol]=="F" and row[idCol]=="BIFAO096_art_03.pdf":            #critère de sélection du corpus test 1 seul fichier
    #if row[langCol]=="F" and isinstance(row[powerCol],str) and row[powerCol].startswith("P"):            #critère de sélection du corpus pouvoir
    if row[langCol]=="F" and (row[yearCol]==1910 or row[yearCol]==2022):            #critère de sélection du corpus pouvoir
        isNecro= isinstance(row[necroCol],str) and row[necroCol].startswith("N")
        isPower =isinstance(row[powerCol],int) and row[nPowerCol].startswith("P")
        s=row[idCol]
        print(s)
        bulletinID=s.split("_")[0]
        articleWithinBulletinID=s.split("_")[-1].split(".")[0]
        #les nécrologies ont été nettoyées à la main -> on va chercher, dans ce cas, dans un répertoire spécifique (avec un nom de fichier différent)
        shortId=bulletinID+"_"+articleWithinBulletinID
        if isNecro:
            textPath=os.path.join(necrologiesTextFolder,bulletinID+"_"+articleWithinBulletinID+"_main.txt")
            footNotesPath=os.path.join(necrologiesTextFolder,bulletinID+"_"+articleWithinBulletinID+"_footnotes.txt")
        else:
            textPath=os.path.join(textsFolder,bulletinID+"_art_"+articleWithinBulletinID+".pdf_main.txt")
            footNotesPath=os.path.join(textsFolder,bulletinID+"_art_"+articleWithinBulletinID+".pdf_footnotes.txt")
        spacyJsonPath=os.path.join(jsonFolder,s+".json")
        if os.path.exists(spacyJsonPath):
            ftemp=open(spacyJsonPath,"r")
            l = json.load(ftemp)
            ftemp.close()
        else:
            l=serializeSpacyDoc(spacyDocFromPath(textPath))
        #l contient parfois des caractères de contrôle unicode -> à nettoyer
        for t in l:
            t["lemma"]="".join(ch for ch in t["lemma"] if unicodedata.category(ch)[0]!="C")
            t["text"]="".join(ch for ch in t["text"] if unicodedata.category(ch)[0]!="C")
        dMetadata={"auteur": row[authorCol], "annee":str(row[yearCol]), "titre":row[titleCol]}
        if isNecro:
            dMetadata["nomDefunt"]=row[deceasedNameCol]
            dMetadata["metierDefunt"]=row[deceasedJobCol]
            dMetadata["categ"]="Nécrologie"
        elif isPower:
            dMetadata["categ"]="Pouvoir"     
        articleWithinBulletinIDTrimmed=articleWithinBulletinID[0:2]
        sSourceURL="https://www.ifao.egnet.net/bifao/"+str(int(bulletinID[-3:]))+"/"+str(int(articleWithinBulletinIDTrimmed))+"/"
        sFootnotes=""
        if os.path.exists(footNotesPath):
            fFootnotes=open(footNotesPath,"r",encoding="utf-8")
            sFootnotes=fFootnotes.read()
            fFootnotes.close()
        if blOutputTEI:
            #r=generateXmlForText(shortId,sSourceURL,s,l,dMetadata,sFootnotes,isNecro)
            r=generateXmlForText(dMetadata["titre"],sSourceURL,s,l,dMetadata,sFootnotes,isNecro)
            etree.ElementTree(r).write(os.path.join(corpusOutputFolder,shortId+".xml"),xml_declaration=True,encoding="utf-8")
        if blOutputHyperbase10Individual:
            #On ne prend que les caractères alphanumériques de la valeur des attributs des textes
            sHyperbase10Output+="**** "+" ".join(["*"+k+"_"+"".join(ch for ch in dMetadata[k] if ch.isalnum()) for k in dMetadata])+"\n"
            for t in l:
                if not(t["text"].startswith("@")):
                    sHyperbase10Output+="\n"+t["text"]+"\t"+t["pos"]+"\t"+t["lemma"]+"\n"
        if blOutputHyperbase10GroupedByBulletin:
            separatorToken = {"text":"-------------------","pos":"X","lemma":"-----------------"}
            headerToken = {"text":s,"pos":"X","lemma":s}
            if not(bulletinID) in dByBulletin:
                dByBulletin[bulletinID]={"annee":row[yearCol],"tokens":[headerToken]}
            dByBulletin[bulletinID]["tokens"]+=[separatorToken]+[headerToken]+l

if blOutputHyperbase10GroupedByBulletin:
    for b in dByBulletin:
        sHyperbase10Output+="**** *annee_"+str(dByBulletin[b]["annee"])+" *bulletin_"+b+"\n"
        sHyperbase10Output+="".join(["\n"+t["text"]+"\t"+t["pos"]+"\t"+t["lemma"]+"\n" for t in dByBulletin[b]["tokens"] if not(t["text"].startswith("@"))])
        #for t in dByBulletin[b]["tokens"]:
        #    if not(t["text"].startswith("@")):
        #        sHyperbase10Output+="\n"+t["text"]+"\t"+t["pos"]+"\t"+t["lemma"]+"\n"

if blOutputHyperbase10Individual or blOutputHyperbase10GroupedByBulletin:
    f=open(corpusOutputHyperbase10Path,"w",encoding="utf-8",newline="")
    f.write(sHyperbase10Output)
    f.close()


print("Corpus generated")

