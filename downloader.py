#! /Library/Frameworks/Python.framework/Versions/3.7/bin/python3
import subprocess
import argparse
import re
import time
import sys
import http
import atexit
import os
from bs4 import BeautifulSoup
from urllib import request

def exit_proc():
    os.remove(addrfile)
    os.remove(pdffile)
    os.remove(txtfile)
def setOrDefault(match):
    return match[1] if match is not None else ""

def printrow(rowmap, outfile):
    data = []
    for heading in ["name", "date", "address", "sample type", "sampling point", "sample source", "arsenic","chromium","lead","manganese","mercury",
    "ph","nitrate","nitrite"]:
        data.append(rowmap.get(heading,""))
    print(",".join(data), file=outfile)

def process_pdf(infile, addrfile, outfile, name, date):
    
    with open(addrfile) as f:
        lines = list(filter(lambda x: not (re.match("\"+", x) or re.match("^\s*$",x)), map(lambda x: x.replace("\"",""),f.read().splitlines())))
        print(lines)
        if len(lines) > 1:
            addr = lines[-2]+" "+lines[-1]
        else:
            addr = "null"
        rowmap = {"name":"\""+(lines[0] if re.match("\d+\.\s,\s*", name) else name) +"\"", "address":"\""+addr+"\"",
		 "date": "\""+ date +"\""}
    with open(infile) as f:
        fulltext = f.read()
    
    rowmap["sample type"] = setOrDefault(re.search("Sample\s*Type:(?:,|\s)*(.*?)(?:,|Sampling Point)",fulltext, re.IGNORECASE)).strip()
    rowmap["sampling point"] = setOrDefault(re.search("Sampling\s*Point:(?:,|\s)*(.*?)(?:,|Well Permit)", fulltext, re.IGNORECASE)).strip()
    rowmap["sample source"] = setOrDefault(re.search("Sample\s*Source:(?:,|\s)*(.*?)(?:,|Receipt Temp)",fulltext, re.IGNORECASE)).strip()
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
parser = argparse.ArgumentParser(description="Extract well water data from an NC county lab")
parser.add_argument("url", help="A url to the directory page containing links to pdfs")
parser.add_argument("-o","--output", dest="filename", default="yams.csv", help="The filename for output csv (include the .csv). Default is yams.csv")
parser.add_argument("--shm", action="store_true")
args = parser.parse_args()
url = args.url
filename = args.filename
timestamp = str(time.time())
prefix = ("/dev/shm/" if args.shm else "")+timestamp
addrfile = prefix+"-addr.txt"
pdffile = prefix+"-yams.pdf"
txtfile = prefix+"-yams.txt"
atexit.register(exit_proc)
page = None
try:
    page = request.urlopen(url).read()
except (http.client.IncompleteRead) as e:
    page = e.partial
except:
    print("Failed to load directory page -- Aborting")
    sys.exit(0)

page = page.decode("utf-8")

soup = BeautifulSoup(page,features="html.parser")
with open(filename,"w",1) as csv:
    print("name, date, address, sample type, sampling point, sample source, arsenic,chromium,lead,manganese,mercury,ph,nitrate,nitrite",file=csv)
    for index, row in enumerate(soup.find_all(class_="row")[1:]): 
        name = row.contents[1].string
        date = row.contents[5].string
        #Ignore no-names
        href = row.contents[3].a["href"]
        subprocess.run(["curl","-o", pdffile, "-H", "User-Agent: Mozilla", "-L", "https://celr.ncpublichealth.com/"+href, "--silent"])
        subprocess.run(["java", "-jar", "tabula-1.0.2-jar-with-dependencies.jar", "-a", "%30,0,82,100", "-f", "CSV", "-o" , txtfile, pdffile])
        subprocess.run(["java", "-jar", "tabula-1.0.2-jar-with-dependencies.jar", "-a", "%20,55,30,100", "-f", "TSV", "-o",addrfile, pdffile])
        try:
            process_pdf(txtfile, addrfile, csv, name, date)
        except Exception as e:
            print("PDF Parsing for "+name+" failed because "+str(e))
    
