import os
import sys
import twitter
import networkx as nx
import pickle
import datetime
import liwc
import math
import time
import random

from whoosh import fields, index
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin
from whoosh.qparser import GtLtPlugin

from twitter.oauth import write_token_file, read_token_file
from twitter.oauth_dance import oauth_dance


# Go to http://twitter.com/apps/new to create an app and get these items
# See also http://dev.twitter.com/pages/oauth_single_token

APP_NAME = 'CSCS/SOC 260'
CONSUMER_KEY = 'xPszGbQonsIFz0Ldz9zf8w'
CONSUMER_SECRET = 's0hlqWZE9YFIS8XE2rZP2A10L3u5Xh4loc4lpaQkQ'

TWIT_PIPE = None
NET = nx.DiGraph()
INDEX = None
if not os.path.exists("data"):
    os.mkdir("data")

CATS = ['WC', 'WPS', 'Sixltr', 'Dic', 'Numerals','funct', 'pronoun', 'ppron', 'i', 
        'we', 'you', 'shehe', 'they', 'ipron', 'article', 'verb', 'auxverb', 'past', 
        'present', 'future', 'adverb', 'preps','conj', 'negate', 'quant', 'number',
        'swear', 'social', 'family', 'friend', 'humans', 'affect', 'posemo', 'negemo',
        'anx', 'anger', 'sad', 'cogmech','insight', 'cause', 'discrep', 'tentat', 
        'certain', 'inhib', 'incl', 'excl','percept', 'see', 'hear', 'feel', 'bio', 
        'body', 'health', 'sexual', 'ingest', 'relativ', 'motion', 'space', 'time', 
        'work', 'achieve', 'leisure', 'home', 'money', 'relig', 'death', 'assent',
        'nonfl', 'filler','Period', 'Comma', 'Colon', 'SemiC', 'QMark', 'Exclam', 
        'Dash', 'Quote', 'Apostro', 'Parenth', 'OtherP', 'AllPct']
        
        
MONTHS = {"Jan":1, "Feb":2, "Mar":3, "Apr":4, "May":5, "Jun":6, "Jul":7, "Aug":8, "Sep":9, "Oct":10, "Nov":11, "Dec":12}

def create_index():
    global INDEX
    if not os.path.exists("twitter_index"):
        os.mkdir("twitter_index")

    schema = fields.Schema(id=fields.ID(stored=True,unique=True),
                            batch=fields.NUMERIC(stored=True), 
                            content=fields.TEXT(stored=True), 
                            posted=fields.DATETIME(stored=True),   
                            owner=fields.TEXT(stored=True),  
                            isRT=fields.BOOLEAN(stored=True), 
                            timesRT=fields.NUMERIC(stored=True),
                            timesFav= fields.NUMERIC(stored=True),
                            hashtags=fields.KEYWORD(stored=True),
                            orgnlTweet = fields.TEXT(stored=True),
                            mentions=fields.KEYWORD(stored=True),
                            replyToUser=fields.TEXT(stored=True),
                            replyToTweet=fields.ID(stored=True),
                            hasPic = fields.BOOLEAN(stored=True),
                            url = fields.TEXT(stored=True),                        
                            liwc=fields.TEXT(stored=True))
                    
    
    INDEX = index.create_in("twitter_index", schema, indexname="TWTTR")
    print "New searching index succesfully created" 
    
    return INDEX
    
    
def clear_index():
    stem = os.getcwd()
    files = os.walk("twitter_index")
    for i in files:
        for j in i[2]:
            try:
                os.remove(stem+"/twitter_index/"+j)
            except:
                os.remove(stem+"/twitter_index/TWTTR.tmp/"+j)
    
    create_index()
                
                
def login(app_name=APP_NAME,consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET, 
                token_file='out/twitter.oauth'):
                
    global TWIT_PIPE
    try:
        (access_token, access_token_secret) = read_token_file(token_file)
    except IOError, e:
        (access_token, access_token_secret) = oauth_dance(app_name, consumer_key,
                consumer_secret)

        if not os.path.isdir('out'):
            os.mkdir('out')

        write_token_file(token_file, access_token, access_token_secret)

        print >> sys.stderr, "OAuth Success. Token file stored to", token_file

    TWIT_PIPE = twitter.Twitter(auth=twitter.oauth.OAuth(access_token, access_token_secret,
                           consumer_key, consumer_secret))


def cleanName(name):
    global TWIT_PIPE
    #print "cleaning name "+str(name)
    try:
        if type(name) == int:
            id = int(name)
            sn = TWIT_PIPE.users.show(user_id=id)["screen_name"]
        else:
            sn = name
            id = TWIT_PIPE.users.show(screen_name=name)["id"]
        
        return [sn,int(id)]
    except:
        return ["error",-1]



def viewUser(name, save=True):
    global TWIT_PIPE
    global NET
    
    usn,id = cleanName(name)
        
    data = TWIT_PIPE.users.lookup(screen_name=usn, entities=False)
    
    print "Name:\t\t", data[0]["name"]
    name = data[0]["id"]
    print "ID:\t\t", id
    print "Tweets:\t\t", data[0]["statuses_count"]
    print "Followers:\t", data[0]["followers_count"]
    print "Friends:\t\t", data[0]["friends_count"]
    print "Joined:\t\t", data[0]["created_at"]
    
    if save:
        NET.add_node(id)
        NET.node[id]["friends_count"]=data[0]["friends_count"]
        NET.node[id]["followers_count"]=data[0]["followers_count"]
     
    strg = "<p><h3><li>User Name:\t" +str(usn)+"</li></h3>"    
    strg += "<li>User ID:\t"+str(id)+"</li><li>Tweets: "+str(data[0]["statuses_count"])+"</li>"
    strg += "<li> Followers:\t "+str(data[0]["followers_count"]) +"</li>"
    strg += "<li> Friends:\t"+str(data[0]["friends_count"])+"</li>"
    strg += "<li> Joined:\t" +str(data[0]["created_at"])+"</li></p>"
    return strg


def getFriends(name, save=True):
    global NET

    usn,id = cleanName(name)
    
    friends = []
    next_cursor = -1
    while next_cursor != 0 and len(friends) < 30000:
        time.sleep(random.randint(0,15))
        data = TWIT_PIPE.friends.ids(screen_name=usn,cursor=next_cursor)
        friends += data["ids"]
        next_cursor = data["next_cursor"]
    
    #print friends
    #print data
    
    try:
        NET.node[id]
    except:
        NET.add_node(id)
    
    if save:
        for i in friends:
            NET.add_node(i)
            NET.add_edge(i, usn)
    
        NET.node[id]["friends"] = friends
    
    return friends

def getFollowers(name, save=True):
    global NET

    usn,id = cleanName(name)
    followers = []
    next_cursor = -1
    while next_cursor != 0 and len(followers) < 30000:
        time.sleep(random.randint(0,15))
        data = TWIT_PIPE.followers.ids(screen_name=usn,cursor=next_cursor)
        followers += data["ids"]
        next_cursor = data["next_cursor"]
    #print followers
    
    try: 
        NET.node[id]
    except:
        NET.add_node(id)
        
    if save:
        for i in data:
            NET.add_node(i)
            NET.add_edge(usn,i)
    
        NET.node[id]["followers"] = followers
      
    return followers  

def getUsersTweets(name, count=200):
    global TWIT_PIPE
    
    usn,id = cleanName(name)
    
    tweets = TWIT_PIPE.statuses.user_timeline(screen_name=usn,count=count) 
    
    print int(len(tweets)), " tweets from ", usn
    for i in tweets:
        #print i
        isRT = False
        if "RT @" in i["text"] or "RT@" in i["text"]:
            isRT = True
        print "__"*15
        print "TweetID:\t\t", i["id"]
        print
        print "Posted:\t\t",i["created_at"]
        print "Text:\t\t",i["text"][:90]+"\n\t\t"+i["text"][90:]
        #print "Hashtags:\t", i["entities"]["hashtags"][0]["text"]
        mens = []
        mentions = i["entities"]["user_mentions"]
        for j in mentions:
            print "Mentions:\t", j["screen_name"]
        rt = i["retweet_count"]
        print "Is Retweet:\t", isRT
        if rt == False:
            print "Times RT'd:\t", 0
        else:
            print "Times RT'd:\t", rt
        fv = i["favorite_count"]    
        print "Times Fav'd:\t", fv

    return tweets            


def index_Tweets(tweets, batch=1):

    
    if type(batch) != int:
        print "Invalid batch name. It needs to be a number. Tweets not added to the index."
    
    elif type(INDEX) == None:
        print "The INDEX has not yet been created"
    
    else:       
        try:
            ix = index.open_dir("twitter_index", indexname="TWTTR")
            w = ix.writer()
        except:
            ix = create_index()
            w = ix.writer()
        for i in range(len(tweets)):
            tw = cleanTweet(tweets[i])
            #print tw

            w.add_document(id = unicode(tw["id"]),
                                batch = int(batch), 
                                content = unicode(tw["text"]), 
                                posted = tw["posted"],   
                                owner = unicode(tw["sn"]),
                                hashtags = tw["hashtags"],
                                mentions = unicode(tw["mentions"]), 
                                replyToTweet = unicode(tw["replyToStatus"]),
                                replyToUser = unicode(tw["replyToSN"]), 
                                isRT = bool(tw["isRT"]), 
                                timesRT = int(tw["rt_count"]),
                                timesFav = int(tw["fav'd"]),
                                orgnlTweet = unicode(tw["orig"]),
                                hasPic = bool(tw["hasPic"]),
                                url = unicode("./tools/nodata.html"), 
                                liwc = unicode(tw["liwc"]))
        w.commit()
        return tw                        


def cleanTweet(tweet):
    cleaned = {}
    
    #print tweet
    isRT = False
    if "RT @" in tweet["text"] or "RT@" in tweet["text"]:
        isRT = True
        try:
            #print tweet
            cleaned["orig"] = tweet["retweeted_status"]["id"]
        except:
            print "didn't get original tweet id"
            cleaned["orig"] = "unknown"
    else:
        cleaned["orig"] = "NA"
    cleaned["isRT"] = isRT
    
    rt = tweet["retweet_count"]
    if rt == False:
        rt = 0
    cleaned["rt_count"] = rt
        
    fv = tweet["favorite_count"]
    cleaned["fav'd"] = fv
    
    ent = tweet["entities"]     
    ht = ",".join([x["text"] for x in ent["hashtags"]])
    if ht =='':
        ht = []
    cleaned["hashtags"] = ht
    
    try:
        cleaned["hasPic"] = False
        md = tweet["entities"]["media"]
        for i in range(len(md)):
            if tweet["entities"]["media"][i]["type"] == u'photo':
                cleaned["hasPic"] = True
    except:
        cleaned["hasPic"] = False
        
   
    sn = []
    for m in ent["user_mentions"]:
        sn.append(m["screen_name"])
    cleaned["mentions"] = ",".join(sn)
    
    cleaned["sn"] = tweet["user"]["screen_name"]
    cleaned["id"] = tweet["id"]
    
    cleaned["replyToStatus"]= tweet["in_reply_to_status_id"]
    
    cleaned["replyToSN"]= tweet["in_reply_to_screen_name"]
    
    cleaned["text"] = tweet["text"]
    
    
    cleaned["posted"] = to_datetime(tweet["created_at"])                                 
    cleaned["liwc"] = liwc_parse(tweet["text"])

    return cleaned
    
def to_datetime(created_at):

    d = created_at.split(" ")
    t = d[3].split(":")
    
    return datetime.datetime(int(d[5]),int(MONTHS[d[1]]), int(d[2]), int(t[0]),     
                                            int(t[1]),int(t[2]),int("00"))
                                            
                                            
def search(terms, limit=100, time_slice=None, saveAs="search"):

    big_tables = {}
    for i in CATS:
        big_tables[i]=[]
    
    f = open("./"+saveAs+"_results.html", "w+")
    master_str = "<!DOCTYPE html><html><style>hr {border: 4;width: 80%;}</style>"+ "<title>Search Results [term(s): "+terms+"]</title><body><br>"
    
    ix = index.open_dir("twitter_index", indexname="TWTTR")
    w = ix.writer()
    qp = QueryParser("content", schema=w.schema)
    qp.add_plugin(DateParserPlugin())
    qp.add_plugin(GtLtPlugin())
    q = qp.parse(terms)
    list_IDs =[]    
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
            list_IDs.append(int(res["id"]))
            to_nums(res["liwc"], big_tables)
            master_str += to_html(res, True)
        
        master_str += "</body></html>"
        f.write(master_str)
        f.close()
        
        res_str = "<!DOCTYPE html><html><title>LIWC statistics for term(s):"+terms+"</title><body><br>"
        res_str += "<table><tr>"+("<th>Category&nbsp;</th><th>Average</th><th>Std Dev</th><th>Max&nbsp</th><th>Min&nbsp</th>"*3)+"</tr>"
        count = 0
        for_later = {}
        for j in big_tables.keys():
            vals = big_tables[j]
            #print j, vals
            outputs = []
            if len(vals) != 0:
                avg = sum(vals)/float(len(vals))
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
            
            
            res_str += "<td>"+str(j)+"</td><td>"+str(outputs[0])+"</td><td>"+str(outputs[1])
            res_str += "</td><td>"+str(outputs[2])+"</td><td>"+str(outputs[3])+"</td>"
            count +=1
            if count%3 == 0:
                res_str+= "</tr>"
            for_later[j] = outputs
        
        res_str+="</table>"
    
        if big_tables["WC"] == []:
            big_tables = ""
            res_str = "<!DOCTYPE html><html><title>LIWC statistics for term(s): "
            res_str += terms+"</title><body><br>" 
            res_str += "<p>No matches found </p></body></html>"
            
        t = open("./"+ saveAs +"_averages.html", "w+")
        t.write(res_str)
        t.close()
        
        graph_Tweets(results,saveAs)
        
    return res_str, for_later, master_str, list_IDs

def to_nums(strg, tables):
    chk = strg[1:-1].split("],[")

    vals = chk[0].split(",")
    for i in range(len(vals)):
        tables[CATS[i]].append(float(vals[i]))
        

def to_html(tweet, withtable):
    """ tweet is a dictionary"""

                    
    print tweet["owner"], " : ", tweet["content"]
    print 
    
    try:
        big_str =  "<h2 style=\"color:DarkBlue\">"+str(tweet["owner"])+"</h2>"
    except:
        big_str = "<h2>Error parsing title</h2>"
        
    big_str += "<p>TweetID: "+str(tweet["id"])+"</p>"
    try:
        big_str += "<p><h3>"+tweet["content"].encode("utf-8")+"</h3></p>"
    except:
        big_str = "<h2>Error parsing tweet text</h2>"

    try:
        big_str += "<li>Posted "+str(tweet["posted"])+"</li>"
        big_str += "<li>Hashtags: " + str(tweet["hashtags"]) + "</li>"
        big_str += "<li>Is a retweet?: " + str(tweet["isRT"]) + "</li>"
        big_str += "<li>Original TweetID: " +str(tweet["orgnlTweet"])+"</li>"
        big_str += "<li>Times retweeted: " + str(tweet["timesRT"]) + "</li>"
        big_str += "<li>Times favorited: " + str(tweet["timesFav"]) + "</li>"
        big_str += "<li>Mentions: " + str(tweet["mentions"]) + "</li>"
        big_str += "<li>Is Reply to User: " +str(tweet["replyToUser"]) + "</li>"
        big_str += "<li>Is Reply to Tweet:" +str(tweet["replyToTweet"]) +"</li>"
        #big_str += "<li>URL:\t\t"+str(tweet["url"])+"</li>"

    except:
        big_str += "<li>Date error, but it's still searchable</li>"
    if withtable:
        #print tweet["liwc"]
        i = tweet["liwc"].replace("[", "").replace("]","")
        big_str += "<p>"+liwc_str_to_html_table(i)+"</p>"
    
    big_str += "<br><hr><br>"
        
        
    return big_str


def liwc_str_to_html_table(strng):
    bos  = "<table><tr>"+("<th>Category&nbsp;&nbsp;</th><th>Percent&nbsp;&nbsp;</th>"*6)+"</tr>"
    count = 0
    ss = strng.split(",")
    #print ss
    for i in range(len(ss)):
        if count%6 == 0:
            bos+= "<tr>"
            
        if float(ss[i]) != 0.0:
            bos += "<td>"+str(CATS[i])+"</td><td>"+str(ss[i])+"</td>"
            count +=1
        if count%6 == 0:
            bos+= "</tr>"
    bos+="</table>"
    
    return bos
       
def liwc_parse(sentence):
    counts = liwc.from_text(sentence)
    reordered = []
    for j in CATS:
        try:
            reordered.append(round(counts[j],4))
        except:
            reordered.append(0)
    
    return reordered  

    
def inspectRetweets(ids):
    
    global TWIT_PIPE
    global NET
    loadNetwork()
       
    ix = index.open_dir("twitter_index", indexname="TWTTR")
    
    retweets = ids

    while retweets != []:
        i = retweets.pop()
        print "Inspecting Tweet #"+str(i)
        htmlname = int(i)
        node_dic = {}
        edges = []
        nodes = []
        count = 0
        isRetweet = True
        
        orig = int(i)
        docs_to_update = []
        docs_to_update.append(orig)
        rts = TWIT_PIPE.statuses.retweets.id(id=i, count=100)
        while isRetweet:
            rttw = TWIT_PIPE.statuses.show(id=i)
            #print rttw
            try:
                i = rttw["retweeted_status"]["id"]
                rts = rts + TWIT_PIPE.statuses.retweets.id(id=i, count=100)
            except:
                if i != orig:
                    rts = rts + TWIT_PIPE.statuses.retweets.id(id=i, count=100)
                    #docs_to_update.append(i)
                isRetweet = False
                
            
        final = int(i)   
        for i in docs_to_update:
            s = ix.searcher()
            doc = s.document(id=unicode(i))
            if doc == None:
                predoc = TWIT_PIPE.statuses.show(id=i)
                print "Printing predoc" + "NNNNN"*20
                print predoc
                doc = index_Tweets([predoc])
            doc = s.document(id=unicode(i))
            #print doc
            post_time = doc["posted"]
            name = "@"+doc["owner"]
            nodes.append("{\"id\":\""+name+"\",\"value\":8,\"color\":\"gray\"}")
            owner_sn, owner_uid = cleanName(doc["owner"])
            ownerhtml = viewUser(owner_uid)
        
    
            node_dic[owner_uid] = count
            count += 1
            url = "./data/"+str(htmlname)+".html"
            w = ix.writer()
            w.update_document(id = doc["id"],
                                    batch = doc["batch"], 
                                    content = doc["content"], 
                                    posted = doc["posted"],   
                                    owner = doc["owner"],
                                    hashtags =doc["hashtags"],
                                    mentions = doc["mentions"], 
                                    replyToTweet = doc["replyToTweet"],
                                    replyToUser = doc["replyToUser"], 
                                    isRT = doc["isRT"], 
                                    timesRT = doc["timesRT"],
                                    timesFav = doc["timesFav"],
                                    orgnlTweet = doc["orgnlTweet"],
                                    hasPic = doc["hasPic"],
                                    url = unicode(url), 
                                    liwc = doc["liwc"])
                                
       
            w.commit()
               
        i = int(final)
        retweeters1 = []
        times = []
        delta_avg = []
        for j in rts:
            #print j["id"]
            #retweets.append(j["id"])
            retweeters1.append(j["user"]["screen_name"])
            times.append(j["created_at"])
            delta = to_datetime(j["created_at"]) - post_time
            
            val = int((24*delta.days) + (delta.seconds/3600.))
            delta_avg.append(val)
            #print val
            try:
                val = node_dic[int(j["user"]["id"])]
            except:
                val =int(count)
                node_dic[int(j["user"]["id"])] = count
                count += 1
            edges.append("{\"source\":"+str(node_dic[owner_uid])+",\"target\":"+str(val)
                            +",\"length\":"+str(val)+"}")
            
            poster_sn = j["retweeted_status"]["user"]["screen_name"]
        

        if retweeters1 != []:
            retweeters = []
            for i in range(len(retweeters1)):
                retweeters.append(cleanName(retweeters1[i])[1]) 
            #o_sn, owner_uid = cleanName(poster_sn)
            try:
                friends = NET.node[owner_uid]["friends"]
            except:
                friends = getFriends(owner_uid)
            try:
                followers = NET.node[owner_uid]["followers"]
            except:
                followers = getFollowers(owner_uid)
             
            saveNetwork()   
            #print "friends", friends
   
            saveNetwork()    
        
            counts = [0,0,0]
            for uid in node_dic:
                
                if uid != owner_uid:
                    if (uid in retweeters):                                
                        if uid in followers:
                            
                            if uid in friends:
                                tw = retweeters1[retweeters.index(uid)]
                                nodes.append("{\"id\":"+("\"@"+str(tw))
                                                +"\",\"value\":5,\"color\":\"blue\"}")
                                counts[1] +=1
                            else:
                                tw = retweeters1[retweeters.index(uid)]
                                nodes.append("{\"id\":"+("\"@"+str(tw))
                                                +"\",\"value\":5,\"color\":\"green\"}")
                                counts[0] +=1
                        else:
                            tw = retweeters1[retweeters.index(uid)]
                            nodes.append("{\"id\":"+("\"@"+str(tw))
                                            +"\",\"value\":5,\"color\":\"purple\"}")
                            counts[2] +=1
                    else:
                        nodes.append("{\"id\":\"UNKNOWN\",\"value\":5,\"color\":\"purple\"}")
                        counts[2] +=1
    
        strg = "{\"nodes\":[\n"
        for k in nodes:
            strg += k + ",\n"
        strg = strg[:-2] + "],\n\"links\":["
        for f in edges:
            strg += f+",\n"
        strg = strg[:-2] + "]}"
    
        file = open("./data/"+str(htmlname)+".json", "w+")
        file.write(strg)
        file.close() 
        dmax = max(delta_avg)
        dmin = min(delta_avg)
        davg = sum(delta_avg)/float(len(delta_avg))
        html = "<p>"+ownerhtml+"<br>"
        html += to_html(doc,True)
        html += "<h4><li>Earliest retweet:\t\t"+str(dmin)+" hour(s) after</li>"
        html += "<li>Last retweet:\t\t\t "+str(dmax)+" hour(s) after</li>"
        html += "<li>Average wait before retweet:\t " +str(davg) +" hour(s)</li>"
        html += "<li>All wait times:\t" +str(delta_avg)+ "</li></h4></p>"
        html += "<br><p>NODE COLORS</p>  <p><h3> green: followers ("+str(counts[0])+") &nbsp&nbsp blue: friends ("+str(counts[1])+") &nbsp&nbsp purple: neither ("+str(counts[2])+")</h3></p>"  
          
    
        form = open("./tools/base.html", "r+")
        file2 = open(url, "w+")
        lines = form.readlines()
        for ln in lines:
            if "<body>" in ln:
                ln = ln + html
            if "fake.json" in ln:
                print "replaced"
                ln = ln.replace("fake.json",str(htmlname)+".json")
            file2.write(ln)
        file.close()
        form.close()
        
         
def tweetSearch(terms, tweet_type="recent"):
    global TWIT_PIPE
    tweets = TWIT_PIPE.search.tweets(q=terms,result_type=tweet_type, count=100)["statuses"] 
    
    print int(len(tweets)), " tweets"
    for i in tweets:
        #print i
        isRT = False
        if "RT @" in i["text"] or "RT@" in i["text"]:
            isRT = True
        print "__"*15
        print "TweetID:\t\t", i["id"]
        print
        print "Posted:\t\t",i["created_at"]
        print "Text:\t\t",i["text"][:90]+"\n\t\t"+i["text"][90:]
        #print "Hashtags:\t", i["entities"]["hashtags"][0]["text"]
        mens = []
        mentions = i["entities"]["user_mentions"]
        for j in mentions:
            print "Mentions:\t", j["screen_name"]
        rt = i["retweet_count"]
        print "Is Retweet:\t", isRT
        if rt == False:
            print "Times RT'd:\t", 0
        else:
            print "Times RT'd:\t", rt
        fv = i["favorite_count"]    
        print "Times Fav'd:\t", fv

    return tweets            
    

def graph_Tweets(results,saveAs):
    owners = {}
    scale = len(results)
    print scale
    for tweet in results:
        try:
            owners[tweet["owner"]].append([tweet["id"], tweet["timesRT"], tweet["timesFav"], tweet["url"]])
        except:
            owners[tweet["owner"]] = [[tweet["id"], tweet["timesRT"], tweet["timesFav"],tweet["url"]]]
    
    size_dict = {}
    #size_list = []
    bs = "{\"name\": \"flare\", \"children\": ["
    for owner in owners:
        bs += "{\"name\":\""+str(owner)+"\",\"children\": ["
        for tw in owners[owner]:
  
            size = tw[1]+8
            bs += "{\"name\":\""+str(tw[0])+"\", \"size\":" + str(size)+", \"fvvale\":" + str(tw[2])+ ",\"url\":\""+str(tw[3])+"\"},"
            #size_list.append(size)
            size_dict[tw[0]] = [size, owner]
                
        bs = bs[:-1] + "]},"
    bs = bs[:-1]+ "]}"
    sl = sorted(size_dict, key=lambda key: size_dict[key][0], reverse=True)
    doc = open("./data/"+saveAs+".json", "w+")
    doc.write(bs)
    doc.close()
    #sl = sorted(size_list)
    id_strg = "<br><br>"
    space = "&nbsp"*10
    for key in sl:
        v = size_dict[key]
        id_strg += "<p>Owner: "+str(v[1])+space+" Retweets: "+str(v[0]-8)+space+" TweetID: "+str(key)+"</p>"
    
    form = open("./tools/tweetpack.html", "r+")
    file = open("./"+saveAs+".html", "w+")
    lines = form.readlines()
    for ln in lines:
        if "search.json" in ln:
            #print "replaced"
            ln = ln.replace("search.json", "./data/"+saveAs+".json")
        if "</body>" in ln:
            ln = id_strg + "</body>"
        file.write(ln)
    file.close()
    form.close()


 
      
def saveNetwork():
    global NET
    output = open('net.pkl', 'wb')
    pickle.dump(NET, output)
    
def deleteNetwork():
    global NET
    os.remove("net.pkl")
    NET = nx.DiGraph()

def loadNetwork():
    global NET
    try:
        input = open("net.pkl", 'rb')
        NET = pickle.load(input)
    except:
        NET = nx.DiGraph()

def LIWC_differences(data1, data2):
        
    res_str = "<!DOCTYPE html><html><title>Differences: Avg, StdDev, Max, Min</title><body><br>"
    res_str += "<table><tr>"+("<th>Category&nbsp;</th><th>Average</th><th>Std Dev</th><th>Max&nbsp</th><th>Min&nbsp</th>"*3)+"</tr>"
    count = 0
    for i in CATS:
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


def LIWC_differences_subset(data1, data2, mylist):

    res_str = "<!DOCTYPE html><html><title>Differences: Avg, StdDev, Max, Min</title><body><br>"
    res_str += "<table><tr>"+("<th>Category&nbsp;</th><th>Average</th><th>Std Dev</th><th>Max&nbsp</th><th>Min&nbsp</th>"*3)+"</tr>"
    count = 0
    for i in CATS:
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

    return res_str