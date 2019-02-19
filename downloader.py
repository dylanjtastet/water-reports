#! /Library/Frameworks/Python.framework/Versions/3.7/bin/python3

import subprocess
import re
from bs4 import BeautifulSoup

def printrow(rowmap, outfile):
    data = []
    for heading in ["name","address", "arsenic","chromium","lead","manganese","mercury",
    "ph","nitrate","nitrite"]:
        data.append(rowmap.get(heading,""))
    print(",".join(data), file=outfile)

def process_pdf(infile, addrfile, outfile,name):
    
    with open(addrfile) as f:
        lines = list(filter(lambda x: not (re.match("\"+", x) or re.match("^\s*$",x)), map(lambda x: x.replace("\"",""),f.read().splitlines())))
        print(lines)
        if len(lines) > 1:
            #addr = lines[-2:]
            addr = lines[-2]+" "+lines[-1]
        else:
            addr = "null"
        rowmap = {"name":"\""+(lines[0] if re.match("\d+\.\s,\s*", name) else name) +"\"", "address":"\""+addr+"\""}
    with open(infile) as f:
        fulltext = f.read()

    cutoff = re.sub("\r\n","\n", fulltext)
    cutoff = cutoff.replace("\"","")
    cutoff = re.sub("^.*Page.*\n", "", cutoff, flags=re.MULTILINE)
    cutoff = re.sub("Report Date:(?:.|\n)*","",cutoff)
    cutoff = re.sub("^(?:.|\n)*Analyte.*\n*","",cutoff)
    cutoff = re.sub(",+",",",cutoff)
    cutoff = re.sub(",\r\n","\n",cutoff)
    cutoff = re.sub("\s?<\s?.*","0", cutoff)

    entries = cutoff.split("\n")[:-1]
    for i in range(0, len(entries)):
        entries[i] = entries[i].split(",")[:2]

    print(entries)
    for entry in entries:
        rowmap[entry[0].strip().lower()] = entry[1]
    
    printrow(rowmap, outfile)




##################  Script start ###############################
subprocess.run(["curl","-o","directory.html", "-H", "User-Agent: Mozilla", "-L", "https://celr.ncpublichealth.com/InOrganicChemistry?client.rasclientId=566000283EH&filterBy=1&recentDay=5&docFrom=&docTo"], capture_output=False)
with open("directory.html") as doc:
    soup = BeautifulSoup(doc, features="html.parser")

with open("yams.csv","w") as csv:
    print("name, address, arsenic,chromium,lead,manganese,mercury,ph,nitrate,nitrite",file=csv)
    for index, row in enumerate(soup.find_all(class_="row")[1:]): 
        name = row.contents[1].string
        #Ignore no-names
        href = row.contents[3].a["href"]
        subprocess.run(["curl","-o","yams.pdf", "-H", "User-Agent: Mozilla", "-L", "https://celr.ncpublichealth.com/"+href],
        capture_output=False)
        subprocess.run(["java", "-jar", "tabula-1.0.2-jar-with-dependencies.jar", "-a", "%45,0,82,100", "-f", "CSV", "-o","yams.txt", "yams.pdf"], 
        capture_output=True)
        subprocess.run(["java", "-jar", "tabula-1.0.2-jar-with-dependencies.jar", "-a", "%20,55,30,100", "-f", "TSV", "-o","addr.txt", "yams.pdf"], 
        capture_output=True)
        try:
            process_pdf("yams.txt", "addr.txt", csv, name)
        except Exception as e:
            print("PDF Parsing for "+name+" failed because "+str(e))
    