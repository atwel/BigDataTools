import bs4 as bs
import urllib
import time
import random
import datetime
import os
import math
import liwc
from whoosh import fields, index
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import GtLtPlugin

cats = ['WC', 'WPS', 'Sixltr', 'Dic', 'Numerals','funct', 'pronoun', 'ppron', 'i', 
        'we', 'you', 'shehe', 'they', 'ipron', 'article', 'verb', 'auxverb', 'past', 
        'present', 'future', 'adverb', 'preps','conj', 'negate', 'quant', 'number',
        'swear', 'social', 'family', 'friend', 'humans', 'affect', 'posemo', 'negemo',
        'anx', 'anger', 'sad', 'cogmech','insight', 'cause', 'discrep', 'tentat', 
        'certain', 'inhib', 'incl', 'excl','percept', 'see', 'hear', 'feel', 'bio', 
        'body', 'health', 'sexual', 'ingest', 'relativ', 'motion', 'space', 'time', 
        'work', 'achieve', 'leisure', 'home', 'money', 'relig', 'death', 'assent',
        'nonfl', 'filler','Period', 'Comma', 'Colon', 'SemiC', 'QMark', 'Exclam', 
        'Dash', 'Quote', 'Apostro', 'Parenth', 'OtherP', 'AllPct']




def get_posts(page="annarbor.craigslist.org/mis",count=50):
    """This basic prompt that retrieves the location of listings from the website.
    It accepts either subject main pages OR search result pages."""
    
    if "http://" not in page:
        page = "http://"+page
        
    if page[-1] == "/":
        page = page[:-1]
    
    q = str(page)
    if "html" not in page:
        stem = "/".join(page.replace("/search", "").split("/")[:-1])  
    else:
        stem = "/".join(page.replace("/search", "").split("/")[:-2])
        
    found = 0
    links = []
    
    # This loop reads as many pages as necessary to get the desired number of links
    while ((found < count) and page!=''):
        try:
            document = urllib.urlopen(page)
        except:
            print "Error getting page"
            document = ""
        soup = bs.BeautifulSoup(document)
        
        page = ''
        x = soup.find_all(attrs={"class":"row"})
        
        for row in x:
            # this looks at individual rows, gets their "a" tags (with row.a) and then gets the href
            address = str(row.a.get("href"))
            if "http://" in address:
                links.append(address)
            else:
                links.append(stem + address)  
            found +=1
    
        nx = soup.find(attrs={"class":"button next"})

        if nx != None:
            #print nx.get("href")
            if "search" in q:
                page = nx.get("href")
                if page == None:
                    page = ""
                elif "http://" not in page:
                    page=stem+nx.get("href")
            else:
                page = stem+nx.get("href")
            
            #print page
            if page==None:
                page=""
        else:
            page=""
            
    if found < count:
        print "Only "+str(found)+" posts were available."
    else:
        print "All %d URLs successfully retrieved" % count
    
    # This trims the links down to the number wanted
    return links[:count] 
 

def create_index():
    
    if not os.path.exists("cl_index"):
        os.mkdir("cl_index")
    schema = fields.Schema(title=fields.TEXT(stored=True), batch=fields.NUMERIC(stored=True), 
                            content=fields.TEXT(stored=True), posted=fields.DATETIME(stored=True),   
                            last_checked=fields.DATETIME(stored=True), 
                            pics=fields.NUMERIC(stored=True), ID=fields.ID(unique=True), 
                            address=fields.TEXT(stored=True), loc=fields.TEXT(stored=True), 
                            coord=fields.TEXT(stored=True), url=fields.ID(stored=True), 
                            prices=fields.TEXT(stored=True), price=fields.NUMERIC(stored=True), 
                            liwc=fields.TEXT(stored=True))

    return index.create_in("cl_index", schema, indexname="CL")
        

def index_posts(links, batch=1):
    
    try:
        ix = index.open_dir("cl_index", indexname="CL")
        w = ix.writer()
    except:
        ix = create_index()
        w = ix.writer()
    random.shuffle(links)
    
    
    for i in links:
        print i
        time.sleep(random.randint(0,4))
        try:
            p = read_page(urllib.urlopen(i))
        except:
            print "Error retrieving page"
            p = {}
        if p != False:
            s = w.searcher()
            try:
                mylist = list(s.document_numbers(ID=unicode(p["ID"])))
            except:
                mylist=[]
            
            if  mylist == []:
                try:
                    w.add_document(title=unicode(p["title"]), batch=int(batch),
                                    content=unicode(p["body"]), posted=p["posted"],                      
                                    last_checked=p["last_checked"], pics = p["pic_cnt"],                
                                    ID=unicode(p["ID"]), address=unicode(p["address"]), 
                                    loc=unicode(p["loc"]), coord=unicode(p["coord"]), 
                                    url=unicode(i), price=int(p["price"]), 
                                    prices=unicode(p["prices"]), liwc=unicode(p["liwc"]))
                except:
                    print "Error parsing a posting: Original"
            else:
                if len(mylist) >1:
                    print "Database inconsistencies, post with title "+str(p["title"])+"not added"
                else:
                    try:
                        print "Updating a post"
                        old = mylist[0]
                        pricesss = unicode(old["price"][:-1]+","+p["price"][1:])
                        liwcs = unicode(old["liwc"][:-1]+","+p["liwc"][1:])
                        w.update_document(title=unicode(p["title"]), batch=old["batch"],
                                            content=unicode(p["body"]), posted=old["posted"],
                                            last_checked=p["last_checked"], pics=old["pic_cnt"],       
                                            ID=unicode(p["ID"]), address=unicode(p["address"]), 
                                            loc=unicode(p["loc"]),coord=unicode(p["coord"]), 
                                            url=unicode(i), prices=pricesss, 
                                            price=int(old["price"]), liwc=liwcs)
                    except:
                        print "Error parsing a posting: Update"
    w.commit()

def update_posts(links=[]):

    if links==[]:
        ix = index.open_dir("cl_index", indexname="CL")
        for i in ix.searcher().documents():
            links.append(i["url"])
    
    index_posts(links)
    


def read_page(document):
    """ This function parses individual postings into a python dictionary."""
    #open("./practice/4120833538.html", "r+")
    soup = bs.BeautifulSoup(document)
    
    # The empty dictionary of information we hope to get from the posts
    pieces = {"pic_cnt":0, "body":"", "title":"", "posted":"", "ID":"", "address":"",
                    "coord":0, "loc":"unknown", "last_checked":datetime.datetime.now(), "prices":[], "price":0 }
     
    t = soup.title.text
    print t
    if ("Page Not Found" not in t ) and (t != ""):
        title = soup.find(attrs={"class":"postingtitle"})
        if title != None:
            title = unicode(title.text).strip()
            pieces["title"] = title
            try:
                pieces["prices"].append(title.split("$")[1].split(" ")[0])
                pieces["price"] = title.split("$")[1].split(" ")[0]
            except:
                do = None
            
        body = soup.find(id="postingbody")
        if body != None:
            try:
                pieces["body"] = str(body.text.replace("&#", "").strip())
            except:
                pieces["body"] = "ERROR PARSING"          
        map = soup.find(attrs={"class":"mapaddress"})
        if map != None:
            pieces["address"] = unicode(map.text).split("(")[0].strip() 

        ps = soup.find_all(attrs={"class":"postinginfo"})
        if ps != None:
            for p in ps:
                a = str(p.text)
                if "Posting ID:" in a:
                    pieces["ID"] = a[12:]
                if "Posted:" in a:
                    pieces["posted"] = to_datetime(a[8:])
      

        tags = soup.find(attrs={"class":"blurbs"})       
        if tags != None:
            m = tags.find_all("li")
            for n in m:
                if "Location:" in str(n.text):
                    pieces["loc"] = unicode(n.text)[11:]

    
        bd = soup.find(attrs={"class":"userbody"})
        if bd != None:
            b = bd.find_all("figure")
            if b != []:
                c = b[0].find_all("div")
                for d in c:
                    if str(d.get("id")) == "thumbs":
                        pieces["pic_cnt"] = len(d.find_all("a"))
                

        at = soup.find_all(id = "attributes")
        if at != None:
            for i in at:
                v = i.find_all("div")[0]
                pieces["coord"] = (str(v.get("data-latitude")),str(v.get("data-longitude")))
   
        mystr = pieces["body"] + pieces["title"]
        counts = liwc.from_text(mystr)
        reordered = []
        for j in cats:
            try:
                reordered.append(round(counts[j],4))
            except:
                reordered.append(0)
   
        pieces["liwc"] = [reordered]
        #print pieces
        return pieces
    else:
        return False
        
            
def to_datetime(CL_time):
    
    dt = CL_time.strip().split(",")
    time = dt[1]
    year = dt[0].split("-")
    time = dt[1].split(":")
    if time[1][2] == "P":
        hour = int(time[0])
        if hour !=12:
            hour = hour+12
    else:
        hour = int(time[0])
         
    return datetime.datetime(int(year[0]),int(year[1]), int(year[2]), hour, int(time[1][1:2]),int("00"),int("00")) 



    
def date_to_str(dts):
    return dts.isoformat(' ')

        
def to_nums(strg, tables):
    chk = strg[2:-2].split("],[")

    vals = chk[0].split(",")
    for i in range(len(vals)):
        tables[cats[i]].append(float(vals[i]))
    
def search(terms, limit=50, time_slice=None):

        
        big_tables = {}
        for i in cats:
            big_tables[i]=[]
            

        f = open("./search_results.html", "w+")
        master_str = "<!DOCTYPE html><html><style>hr {border: 4;width: 80%;}</style><title>Search Results [term(s): "+terms+"]</title><body><br>"
        ix = index.open_dir("cl_index", indexname="CL")
        w = ix.writer()
        qp = QueryParser("content", schema=w.schema)
        qp.add_plugin(DateParserPlugin())
        qp.add_plugin(GtLtPlugin())
        q = qp.parse(terms)
        
        with w.searcher() as s:
            results = s.search(q, limit=limit)
            if time_slice != None:
                within = []
                start = int("".join(time_slice[0].split(":")))
                end = int("".join(time_slice[1].split(":")))
                if (0<=start<=2400) and (0 <=end<=2400):
                    for res in results:
                        time = res["posted"]
                        if time.minute < 10:
                            t = int(str(time.hour)+"0"+ str(time.minute))
                        else:
                            t = int(str(time.hour)+ str(time.minute))
                        
                        if start < end and start <= t <=end:
                            within.append(res)
                        elif end < start and (start <= t or t <= end):
                            within.append(res)
                        else:
                            pass
                    
                    results = within
                else:
                    print "Invalid time slice, no results returned."
                    results = []
            print "%d search results" % len(results)
            print "--"*15
            for res in results:
                to_nums(res["liwc"], big_tables)
                master_str += to_html(res, True)
        
        master_str += "</body></html>"
        f.write(master_str)
        f.close()
        
        res_str = "<!DOCTYPE html><html><title>LIWC statistics for term(s): "+terms+"</title><body><br>"
        res_str += "<table><tr>"+("<th>Category&nbsp;</th><th>Average</th><th>Std Dev</th><th>Max&nbsp</th><th>Min&nbsp</th>"*3)+"</tr>"
        count = 0
        for_later = {}
        for j in big_tables.keys():
            vals = big_tables[j]
            outputs = []
            if len(vals) != 0:
                avg = sum(vals)/len(vals)
                outputs.append(round(avg,4))
                var = [(i-avg)**2 for i in vals]
                std = math.sqrt(sum(var)/len(var))
                outputs.append(round(std,4))
                outputs.append(round(max(vals),4))
                outputs.append(round(min(vals),4))
            else:
                outputs = ["NA","NA","NA","NA"]
            if count%3 == 0:
                res_str+= "<tr>"
            
            
            res_str += "<td>"+str(j)+"</td><td>"+str(outputs[0])+"</td><td>"+str(outputs[1])+"</td><td>"+str(outputs[2])+"</td><td>"+str(outputs[3])+"</td>"
            count +=1
            if count%3 == 0:
                res_str+= "</tr>"
            for_later[j] = outputs
        res_str+="</table>"
    
        if big_tables["WC"] == []:
            big_tables = ""
            res_str = "<!DOCTYPE html><html><title>LIWC statistics for term(s): "+terms+"</title><body><br>" 
            res_str += "<p>No matches found </p></body></html>"
        t = open("./search_averages.html", "w+")
        t.write(res_str)
        t.close()
        
        return res_str, for_later, master_str
    
def liwc_str_to_html_table(strng):
    bos  = "<table><tr>"+("<th>Category&nbsp;&nbsp;</th><th>Percent&nbsp;&nbsp;</th>"*6)+"</tr>"
    count = 0
    ss = strng.split(",")
    #print ss
    for i in range(len(ss)):
        if count%6 == 0:
            bos+= "<tr>"
            
        if float(ss[i]) != 0.0:
            bos += "<td>"+str(cats[i])+"</td><td>"+str(ss[i])+"</td>"
            count +=1
        if count%6 == 0:
            bos+= "</tr>"
    bos+="</table>"
    
    return bos

def read_field(text):
    if text == "" or text == "0" or "None" in text:
        return "None given"
    else:
        return str(text)
        
def to_html(page,withtable):
    """ Page is a dictionary"""
    pieces = {"pic_cnt":0, "body":"", "title":"", "posted":"", "ID":"", "address":"",
                    "coord":0, "loc":"unknown", "last_checked":datetime.datetime.now(), "price":[] }
                    
    print page["title"]
    print 
    
    try:
        big_str =  "<h2>"+str(page["title"])+"</h2>"
    except:
        big_str = "<h2>Error parsing title</h2>"
    try:
        big_str += "<p>"+str(page["content"])+"</p><ul>"
    except:
        big_str = "<h2>Error parsing title</h2>"
    big_str += "<li><a href=\""+str(page["url"])+"\">Link to CL posting</a></li>"
    big_str += "<li>General Location: "+read_field(page["loc"])+"&nbsp;&nbsp;&nbsp;&nbsp;&nbspAddress: "+read_field(page["address"])+"&nbsp;&nbsp;&nbsp;&nbsp;&nbspLat&Long: "+read_field(page["coord"])+"</li>"
    try:
        big_str += "<li>Original posting time: "+date_to_str(page["posted"])+"</li>"
    except:
        big_str += "<li>Date error, but it's still searchable</li>"
    #big_str += "<li>Update times: "+datetimes_to_str(page["updated"])+"</li>"
    if page["prices"] =="[]":
        pstr = "None Given"
    else:
        pstr = page["prices"][1:-1]

    big_str += "<li>Price updates: "+pstr+"</li>"
    big_str += "<li>Pic counts: "+str(page["pics"])+"</li></ul>"
    
    if withtable:
        i = page["liwc"][2:-2].split("],[")
        big_str += "<p>"+liwc_str_to_html_table(i[0])+"</p>"
    
    big_str += "<br><hr><br>"
        
        
    return big_str
    
    
def LIWC_differences(data1, data2):
        
    res_str = "<!DOCTYPE html><html><title>Differences: Avg, StdDev, Max, Min</title><body><br>"
    res_str += "<table><tr>"+("<th>Category&nbsp;</th><th>Average</th><th>Std Dev</th><th>Max&nbsp</th><th>Min&nbsp</th>"*3)+"</tr>"
    count = 0
    for i in cats:
        val1 = data1[i]
        val2= data2[i]
        res = [j-k for j,k in zip(val1, val2)]
        
        if count%3 == 0:
            res_str+= "<tr>"
        
        
        res_str +="<td>"+str(i)+"</td><td>"+str(res[0])+"</td><td>"+str(res[1])+"</td><td>"
        res_str +=str(res[2])+"</td><td>"+str(res[3])+"</td>"
        count +=1
        if count%3 == 0:
            res_str+= "</tr>"
    res_str+="</table>"  
    return res_str
    
    
def get_and_index_posts(site, count, batch):
    p = get_posts(str(site), count=count)
    index_posts(p)
    
def clear_index():
    stem = os.getcwd()
    files = os.walk("cl_index")
    for i in files:
        for j in i[2]:
            try:
                os.remove(stem+"/cl_index/"+j)
            except:
                os.remove(stem+"/cl_index/CL.tmp/"+j)

def LIWC_differences_subset(data1, data2, mylist):

    res_str = "<!DOCTYPE html><html><title>Differences: Avg, StdDev, Max, Min</title><body><br>"
    res_str += "<table><tr>"+("<th>Category&nbsp;</th><th>Average</th><th>Std Dev</th><th>Max&nbsp</th><th>Min&nbsp</th>"*3)+"</tr>"
    count = 0
    for i in cats:
        val1 = data1[i]
        val2= data2[i]
        res = [j-k for j,k in zip(val1, val2)]
        
        if count%3 == 0:
            res_str+= "<tr>"
        
        if i in mylist:
            res_str +="<td>"+str(i)+"</td><td>"+str(res[0])+"</td><td>"+str(res[1])+"</td><td>"
            res_str +=str(res[2])+"</td><td>"+str(res[3])+"</td>"
            count +=1
        
        if count%3 == 0:
            res_str+= "</tr>"
    res_str+="</table>"  
    return res_str