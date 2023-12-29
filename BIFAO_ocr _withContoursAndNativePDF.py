import fitz
import pytesseract
import cv2
import numpy as np
import csv
import json
import os
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
jsonFile = r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate\bifao_papers.json"
rootDir= r"E:\personal\EtudesEgyptologie\DigitalResearch\BIFAOCorpus\Intermediate"
lPDFCharacterReplacements = [(chr(65533),' '), ('ﬀ','ff'), ('ﬁ','fi'), ("\uf6dc","1")]

def sameOrGreaterNumber(a,b):
    return a>b-0.3

def sameNumber(a,b):
    return abs(a-b)<0.3

def pix_to_image(pix):
    bytes = np.frombuffer(pix.samples, dtype=np.uint8)
    img = bytes.reshape(pix.height, pix.width, pix.n)
    return img

#Paramètres: idtypographie, année début, année fin, utiliser OCR (booléen), kernelSize, nombre de colonnes de footnotes,
# fontsizeNoteNumberInNotes, reconvertTexteToImageForOCR, fontSizeCallNote (taille du numéro de la note dans le texte),

# (l'année 2004 pose un problème de ToUniCode et doit etre reconvertie en image)
paramTypographies = [(1,1901,1969,True,30,2,8,False,8.4),
                     (2,1970,1993,True,36,2,8,False,8.4),
                     (3,1994,1994,True,36,3,8,False,8.4),
                     (4,1995,2003,False,30,3,8,False,8.4),
                     (5,2004,2004,True,30,3,8,True,8.4),
                     (7,2005,2006,False,30,3,8,False,7.2),
                     (7,2007,2017,False,30,3,8,False,8.4),
                     (8,2018,2023,False,30,3,7,False,8.4)]
fontSizeNoteText=9.0
fontSizeMainText=12.0
minFontSizeFirstLetterOfText= 40
testYear=2005
testArticle=6
#testArticle=22
testPage=1
#testPage=None
#testPage=37
stopAfterPage = True
stopAfterArticle = True


#nous parcourons tous les articles dans la structure json sauvée par l'étape de scraping du web
#pour chacun, on extrait le texte (soit selon OCR soit nativement du pdf - selon la période et la typographie qui y est associée)
#via la liste paramTypographies

f=open(jsonFile,"r")
articles = json.load(f)
f.close()
for a in articles:
    for pt in paramTypographies:
        nTypoPT,minYearPT,maxYearPT,blOCRPT,kernelSizePT,nColFootNotesPT,fontSizeNoteNumberInNotesPT,blReconvertToImgPT,fontSizeCallNotePT=pt
        if a["year"]>=minYearPT and a["year"]<=maxYearPT:
            blOCR=blOCRPT
            kernelSize=kernelSizePT
            nColFootNotes=nColFootNotesPT
            fontSizeNoteNumberInNotes=fontSizeNoteNumberInNotesPT
            blReconvertToImg=blReconvertToImgPT
            fontSizeCallNote=fontSizeCallNotePT
            break
    if (testYear is not None) and a["year"]<testYear: continue
    articleNumber=int(a["nom_fichier"].split("_")[2].split(".")[0])
    if (testArticle is not None) and articleNumber<testArticle: continue
    kernelSize=30
    sArticleText=""
    sFootNotesText=""
    startPageNumber = int(a["pages"].split(" ")[1].split("-")[0])
    sPDFPath=os.path.join(rootDir,a["nom_fichier"])
    print("Starting {}".format(sPDFPath))
    pdf_file=fitz.open(sPDFPath)
    nPageInPDF=0
    sArticleID = a["nom_fichier"].split("_")[0] + "_" + a["nom_fichier"].split("_")[2].split(".")[0]
    isFirstPageOfArticle=True
    for p in pdf_file.pages(1): #on parcourt toutes les pages du pdf en cours, sauf la première (générée automatiquement par le site BIFAO et ne faisant pas partie de l'article d'origine
        nPageInPDF+=1
        pageNumberInVolume=startPageNumber-1+nPageInPDF
        if (testPage is not None) and pageNumberInVolume<testPage: continue
        if blOCR:
            #la méthode de reconnaissance des blocs est inspirée de
            #https://stackoverflow.com/questions/63960038/how-to-detect-multiple-blocks-of-text-from-an-image-of-a-document
            print("Starting page {}".format(pageNumberInVolume))
            
            sMainOCR=""
            footNoteLevel=-1
            blFoundImg=False;
            if blReconvertToImg:
                blFoundImg=True;
                img=pix_to_image(p.get_pixmap(dpi=300))
                #crop 7% below (footer digitally added)
                img=img[0:int(0.93*img.shape[0]),0:img.shape[1]]
            else:
                ims=p.get_images()
                imnum=ims[0][0]
                if len(ims)>0:
                    img=pix_to_image(fitz.Pixmap(pdf_file,imnum))
                    blFoundImg=True;
            if blFoundImg:
                if img.shape[2]==1:
                    gray=img
                else:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray,(5,5),0)
                ret, thresh1 = cv2.threshold(blur, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV)
                rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernelSize, kernelSize))
                dilation = cv2.dilate(thresh1, rect_kernel, iterations = 1)
                contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL, 
                                                        cv2.CHAIN_APPROX_NONE)
                #puis on essaie d'identifier la paire de contours définissant une note de bas de page d'après les critères suivants
                #Je suis un cadre de note de bas de page "de gauche" si
                # 1. mon bord gauche est "assez à gauche", càd <23% de la largeur de l'image
                # 2. mon bord droit vers le milieu, càd entre 38% et 60% de la largeur de l'image
                # 3. je n'ai "nettement en-dessous de moi" que rien ou des morceaux négligeables, càd des éléments faisant moins de 10% x 10%
                # 4. j'ai une "soeur de droite", càd dont le haut est proche de mon haut (moins de 3% de variation),
                #           dont la largeur est proche de ma largeur (moins de 20% de variation)
                #           et dont la hauteur est entre 50% et 150% de ma hauteur
                #print("Shape")
                #print(gray.shape)
                for cnt in contours: 
                    x, y, w, h = cv2.boundingRect(cnt)
                    #print(x,y,w,h)
                    #Suis-je un footNoteRect de gauche?
                    if x>0.23*gray.shape[1]: continue   #mon bord gauche est trop à droite pour être un bloc de footnote de gauche
                    if x+w<(1/nColFootNotes-0.12)*gray.shape[1] or x+w>(1/nColFootNotes+0.1)*gray.shape[1]: continue
                    blFoundBigBelow=False;
                    for cnt2 in contours:
                        x2,y2,w2,h2 = cv2.boundingRect(cnt2)
                        if y2>y+0.03*gray.shape[0] and w2*h2>0.01*gray.shape[0]*gray.shape[1]:
                            blFoundBigBelow=True
                            break
                    if blFoundBigBelow:
                        #print("Found big below")
                        #print(x2,y2,w2,h2)
                        continue
                    #trouve ma soeur - note de bas de page de droite (s'il y a 2 colonnes) ou du milieu (s'il y a 3 colonnes)
                    blFoundSister=False
                    for cnt2 in contours:
                        x2,y2,w2,h2 = cv2.boundingRect(cnt2)
                        if x2>x+w+1 and y2>y-0.03*gray.shape[0] and y2<y+0.03*gray.shape[0] and w2>0.8*w and w2<1.2*w and h2>0.5*h and h2<1.5*h and not(blFoundSister):
                            blFoundSister=True
                            footNoteLevel=min(y,y2)-5
                            print("For page {}, left footnote is {} {} {} {} and right footnote is {} {} {} {}".format(pageNumberInVolume, x, y, w, h, x2, y2, w2, h2))
                    if footNoteLevel>0:
                        cv2.line(gray,(0,footNoteLevel),(gray.shape[1]-1,footNoteLevel),(0,255,0),5)
                        break
                    if blFoundSister: break
                #maintenant, nous allons tenter d'identifier le premier bloc de texte - qui contient seulement le numéro de la page
                #nous allons prendre une dilation moindre car cette ligne est moins séparée du premier bloc de texte
                bottomOfPageNumberBlock=0
                if nPageInPDF>=2:   #pas de numéro de page sur la première page de l'article
                    l=list(contours)
                    l.sort(key=lambda x: cv2.boundingRect(x)[1])
                    for c in l:
                        #on néglige les trop petits
                        x,y,w,h=cv2.boundingRect(c)
                        if w<gray.shape[1]*0.03 or h<20: continue
                        if h>80: break          #si plusieurs lignes, on OCRise quand même
                        bottomOfPageNumberBlock=y+h+4
                        break
                if bottomOfPageNumberBlock>0:
                        cv2.line(gray,(0,y+h+4),(gray.shape[1]-1,y+h+4),(0,255,0),2)
                for cnt in contours: 
                    x, y, w, h = cv2.boundingRect(cnt)
                    rect = cv2.rectangle(gray, (x, y), (x + w, y + h), (0, 255, 0), 2)
                sPngPath = os.path.join(rootDir,"segmentation",a["nom_fichier"]+"_"+str(pageNumberInVolume)+".png")
                cv2.imwrite(os.path.join(rootDir,sPngPath),gray)
                bottom=gray.shape[0]-1
                if footNoteLevel>0: bottom=footNoteLevel
                imMain=gray[bottomOfPageNumberBlock:bottom,0:gray.shape[1]-1]
                #cv2.imwrite(sPngPath,imMain)
                value, thresh = cv2.threshold(imMain, 60, 255, cv2.THRESH_BINARY)
                sMainOCR=""
                if bottom>bottomOfPageNumberBlock: sMainOCR=pytesseract.image_to_string(thresh, lang='fra')
                print (sMainOCR[0:20])
            sArticleText+="@ARTICLE_"+sArticleID+"_PAGE_"+str(pageNumberInVolume)+" " +sMainOCR+"\n"
            if footNoteLevel>0:
                imFootNotes=gray[footNoteLevel:gray.shape[0]-1,0:gray.shape[1]-1]
                value, thresh = cv2.threshold(imFootNotes, 60, 255, cv2.THRESH_BINARY)
                sFootNotesText+=pytesseract.image_to_string(thresh, lang='fra')+"\n"
        else:   #ce n'est pas de l'ocr,  il faut extraire nativement le texte
            blocks=p.get_text("dict",flags=11)["blocks"]
            sFootNoteTextThisPage=""
            sMainTextThisPage=""
            firstLetterRetained = ""
            for b in blocks:
                sBlockText=""
                blockTop=b["bbox"][1]
                blockBottom=b["bbox"][3]
                isMainText=False
                isFootNote=True
                #print("bbox {}, top {}, bottom {}, height {}".format(b["bbox"],blockTop,blockBottom,p.rect.height))
                if blockBottom>=p.rect.height*0.1  and blockBottom<0.95*p.rect.height: #On exclut l'en-tête et le pied de page
                    #on va explorer chaque block, en comparant la taille des caractères, on déduira s'il s'agit du corps du texte
                    # où de notes de pas de page
                    #On considérera aussi que de petits nombres en début de ligne sont les numéros des notes
                    #Par ailleurs, sur la première page, la première lettre est écrite en très grand dans un autre block
                    #on traitera donc celle-ci spécifiquement
                    #print("New block -------------")
                    isFirstLetterBlock=False
                    hasFoundFirstLetterBlock=False
                    minFontSizeFirstLetterOfText
                    sPreviousRawSpanText=""
                    bPreviousIsNoteNumber=False
                    for l in b["lines"]:
                        isFirstSpan=True
                        lineMustBeDiscarded= False
                        for s in l["spans"]:
                            sRawSpanText=s["text"]
                            #print("Raw span {}".format(sRawSpanText))
                            sSpanText=s["text"]
                            for cr in lPDFCharacterReplacements:
                                  sSpanText=sSpanText.replace(cr[0],cr[1])
                            if sameOrGreaterNumber(s["size"],minFontSizeFirstLetterOfText) and isFirstPageOfArticle and \
                                   firstLetterRetained=="" and len(l["spans"])==1 and not(hasFoundFirstLetterBlock):
                                isFirstLetterBlock=True
                                lineMustBeDiscarded=True
                                hasFoundFirstLetterBlock=True
                                firstLetterRetained=sSpanText
                            if sameOrGreaterNumber(s["size"],fontSizeMainText): isMainText=True
                            #bizarrement, les notes 1 à 9 de 1995 à 2017 semblent contenir le texte 11111, 22222, etc.
                            #de même, les notes à partir de 10 ont 5 lines au début qui se répètent avec le numéro de la note
                            #et le texte de la note, ensuite, commence aussi par ce nombre
                            if isFirstSpan and sSpanText.strip()=="":
                                sSpanText=""
                            print("span " + sSpanText)
                            print(isFirstSpan)
                            print(s["size"])
                            print(sSpanText.strip().isnumeric());
                            if isFirstSpan and sameNumber(s["size"],fontSizeNoteNumberInNotes) and sSpanText.strip().isnumeric():
                                if re.match(r"[0-9]{5}",sSpanText): sSpanText=sSpanText[0:1]
                                bPreviousIsNoteNumber=True
                                #print("current {} previous {}".format(sSpanText,sPreviousRawSpanText))
                                if sSpanText==sPreviousRawSpanText:
                                    sSpanText=""
                                    lineMustBeDiscarded=True
                                else:
                                    sSpanText="@REF_"+sArticleID+"_NOTESTART_"+sSpanText.strip() + " "
                                    isFootNote=True
                            elif bPreviousIsNoteNumber and sSpanText.startswith(sPreviousRawSpanText):
                                sSpanText=sSpanText[len(sPreviousRawSpanText):]
                            else:
                                previousIsNoteNumber=False
                            if len(sSpanText)>20 and sameNumber(s["size"],fontSizeNoteText): isFootNote=True
                            if sameNumber(s["size"],fontSizeCallNote) and sSpanText.strip().isnumeric() and isMainText:
                                sSpanText=" @REF_"+sArticleID+"_NOTECALL_"+sSpanText.strip() + " "
                            isFirstSpan=False
                            if not(isFirstLetterBlock):
                                sBlockText+=sSpanText
                            sPreviousRawSpanText=sRawSpanText
                        if not(lineMustBeDiscarded): sBlockText+="\n"
                    if isMainText and not(isFirstLetterBlock):
                        sMainTextThisPage+=firstLetterRetained+sBlockText
                        firstLetterRetained=""
                    elif isFootNote:
                        sFootNoteTextThisPage+=sBlockText
                    else:
                        print("Cannot determine {}".format(sText))
            sArticleText+="@ARTICLE_"+sArticleID+"_PAGE_"+str(pageNumberInVolume)+" " +sMainTextThisPage+"\n"
            sFootNotesText+=sFootNoteTextThisPage
        isFirstPageOfArticle = False
        if stopAfterPage: stop #breakpoint()
            
    sTextPath=os.path.join(rootDir,"texts",a["nom_fichier"]+"_main.txt")
    f=open(sTextPath,"w",encoding="utf-8")
    f.write(sArticleText)
    f.close()
    if sFootNotesText!="":
        sTextPath=os.path.join(rootDir,"texts",a["nom_fichier"]+"_footnotes.txt")
        f=open(sTextPath,"w",encoding="utf-8")
        f.write(sFootNotesText)
        f.close()
    if stopAfterArticle: stop #breakpoint()



