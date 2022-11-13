from flask import Flask, request, jsonify,render_template,redirect,url_for,send_file,session,g,Response
from flask import json
from collections import defaultdict
import socket   
import ast
import requests
import random
import datetime
import sqlite3
import os
import logging
import json
import urllib.request
from math import sin, cos, sqrt, atan2, radians


application = Flask(__name__,
            static_url_path='', 
            static_folder='web/static')

application.config["upload_folder"] = 'web/static/images/'
application.config["upload_folder2"] = 'web/static/'

application.config['SECRET_KEY']='mysecret'
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@application.before_request 
def before_request():
    g.admin = None
    if 'admin' in session:
        g.admin = session['admin']


#################### User Start ##################################

@application.route("/", methods=['GET','POST'])                 
def index():
    # firstsent(1,[76.94749, 8.505766],1,1)                  
    if request.method=='POST':
        data=request.form
        coord=getcoordinates(data['place'])
        xx=datetime.datetime.now()
        query="INSERT INTO 'DISASTERS'(dis_type,dis_reporterPh,dis_place,dis_severity,dis_datetime,dis_geolocation) values('%s','%s','%s','%s','%s','%s')"%(data['disastername'],data['phone'],data['place'],data['severity'],xx.strftime("%m/%d/%Y, %H:%M:%S"),coord)
        detail=inUP(query)
        if detail!=False:
            query="SELECT MAX(dis_id) from DISASTERS"
            detail=selection(query)
            if detail!=False:
                for d in detail:           
                    query="INSERT INTO DISASTER_MANGEMENT(dis_id) values('%s')"%(d[0])
                    print(query)
                    if inUP(query):
                        for i in range(1,5):
                            firstsent(i,coord,d[0],1)                  
            return render_template('index.html',response='200')
        else:
            return render_template('index.html',response='404')
    return render_template('index.html')

@application.route("/dms_notification", methods=['GET','POST'])                 
def dms_notification():

    req_id=request.args.get('id')
    query="SELECT service_status,service_type from REQUESTS WHERE req_id='%s'"%(req_id)
    detail=selection(query)
    if detail!=False:
        for d in detail:
            status=d[0]
            type=d[1]

    if request.method=='POST':
        if status=='In Progress':
            data=request.form['response']
            if data=='1':
                txt='ACCEPTED'
            else:
                txt='DECLINED'
                query="SELECT dis_geolocation,dis_id FROM DISASTERS WHERE dis_id=(SELECT dis_id FROM REQUESTS WHERE req_id='%s')"%(req_id)
                detail=selection(query)
                if detail!=False:
                    for d in detail:
                        firstsent(type,ast.literal_eval(d[0]),d[1],2)                  
            query="UPDATE REQUESTS set service_status='%s', service_time='%s' where req_id='%s'"%(txt,datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),req_id)
            inUP(query)
        else:
            return render_template('services.html',id=404)
         
    item=[]
    query='SELECT dis_place,dis_reporterPh,dis_severity,dis_type,dis_datetime from DISASTERS WHERE dis_id=(SELECT dis_id from REQUESTS WHERE req_id=%s)'%(req_id)
    detail=selection(query)
    if detail!=False:
        for d in detail:
            x={
                'dis_place':d[0],
                'dis_reporterPh':d[1],
                'dis_severity':d[2],
                'dis_type':d[3],
                'dis_time':d[4],
                'req_id':req_id
            }
            item.append(x)
    if request.method=='POST':
        return render_template('services.html',id=200,item=item)
    return render_template('services.html',item=item)


@application.route("/dms_disasters", methods=['GET','POST'])                 
def dms_disasters():
    item=[]
    # query="SELECT DISASTER_MANGEMENT.dis_id,DISASTER_MANGEMENT.dis_ambulance,DISASTER_MANGEMENT.dis_police,DISASTER_MANGEMENT.dis_FF,DISASTER_MANGEMENT.dis_hosp,DISASTERS.dis_place,DISASTERS.dis_datetime FROM DISASTER_MANGEMENT INNER JOIN DISASTERS ORDER BY DISASTERS.dis_id DESC"
    query="SELECT dis_id,dis_ambulance,dis_police,dis_FF,dis_hosp FROM DISASTER_MANGEMENT WHERE dis_id  IN (SELECT dis_id FROM DISASTERS ORDER BY dis_id DESC)"
    if request.method=='POST':
        date=request.form['date']
        date=datetime.datetime.strptime(date,'%Y-%m-%d')
        date=date.strftime("%m/%d/%Y")
        # query="SELECT DISASTER_MANGEMENT.dis_id,DISASTER_MANGEMENT.dis_ambulance,DISASTER_MANGEMENT.dis_police,DISASTER_MANGEMENT.dis_FF,DISASTER_MANGEMENT.dis_hosp,DISASTERS.dis_place,DISASTERS.dis_datetime FROM DISASTER_MANGEMENT INNER JOIN DISASTERS WHERE DISASTERS.dis_datetime LIKE '%s' ORDER BY DISASTERS.dis_id DESC"%(str(date)+'%')
        query="SELECT dis_id,dis_ambulance,dis_police,dis_FF,dis_hosp FROM DISASTER_MANGEMENT WHERE dis_id  IN (SELECT dis_id FROM DISASTERS WHERE dis_datetime LIKE '%s' ORDER BY dis_id DESC)"%(str(date)+'%')
        print(query)
    detail=selection(query)
    if detail!=False:
        for d in detail:
            query="SELECT dis_place,dis_datetime FROM DISASTERS WHERE dis_id=%s"%(d[0]) 
            detail1=selection(query)
            if detail1!=False:
                for d1 in detail1:
                    x={
                        'dis_place':d1[0],
                        'dis_datetime':d1[1],
                        'dis_ambulance':None,
                        'dis_police':None,
                        'dis_FF':None,
                        'dis_hospital':None
                    }
            for i in range(1,5):
                query="SELECT service_location FROM SERVICES WHERE service_id='%s'"%(d[i])
                detail1=selection(query)
                if detail1!=False:
                    for d1 in detail1:
                        location=d1[0]
                query="SELECT service_status,service_time FROM REQUESTS WHERE service_id='%s' and dis_id='%s'"%(d[i],d[0])
                detail1=selection(query)
                if detail1!=False:
                    for d1 in detail1:
                        if i==1:
                            clm='dis_ambulance'
                        elif i==2:
                            clm='dis_police'
                        elif i==3:
                            clm='dis_FF'
                        elif i==4:
                            clm='dis_hospital'
                        x[clm]={
                            "location":location,
                            'service_time':d1[1],
                            'service_status':d1[0]
                        }
            item.append(x)
        return render_template('notification.html',item=item)                               

#################### User End ##################################
#################### FUNCTIONS Start ################################

@application.route("/sentphone", methods=['GET','POST'])      
def sentphone():
    data=request.form['data']
    print(data)
    xx = random.randint(1111,9999)
    text="Your OTP for registering your Disaster in the DMS platform is %s"%(xx)
    resp=sentSMS(data,text)
    return str(xx)     

def firstsent(st,dis_geolocation,dis_id,type):
    data= defaultdict(list)
    phone=defaultdict(list)
    query="SELECT service_id,service_geolocation,service_phone FROM SERVICES where service_type='%s'"%(st)
    detail=selection(query)
    if detail!=False:
        for d in detail:
            xx=ast.literal_eval(d[1])
            data[str(d[0])].append(distancecalculator(dis_geolocation,xx))
            phone[str(d[0])].append(d[2])
        try:
            if len(detail)!=0:
                data=dict(sorted(data.items(), key=lambda item: item[1]))
                if type!=1:
                    query="SELECT service_id FROM REQUESTS where dis_id='%s' AND service_type='%s' AND service_status='In Progress' ORDER BY req_id DESC LIMIT 1"%(dis_id,st)
                    detail=selection(query)
                    if detail!=False:
                        for d in detail:
                            keys=list(data.keys())
                            index=keys.index(str(d[0]))
                            index=index+1
                            res=keys[index]
                            res=res[0]
                elif type==1:
                    temp = min(data.values())
                    res = [key for key in data if data[key] == temp]
                    res=res[0]
        
                query="INSERT INTO 'REQUESTS'(dis_id,service_id,service_type,service_status) values('%s','%s','%s','%s')"%(dis_id,res,st,'In Progress')
                inUP(query)
                if int(st)==1:
                    clm='dis_ambulance'
                elif int(st)==2:
                    clm='dis_police'
                elif int(st)==3:
                    clm='dis_FF'
                elif int(st)==4:
                    clm='dis_hosp'

                query="UPDATE DISASTER_MANGEMENT SET %s=%s WHERE dis_id=%s"%(clm,res,dis_id)
                inUP(query)

                query="SELECT MAX(req_id) from REQUESTS"
                detail=selection(query)
                if detail!=False:
                    for d in detail:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect(("8.8.8.8", 80))
                        IPAddr=(s.getsockname()[0])
                        s.close() 
                        link='http://'+str(IPAddr)+':5500/dms_notification?id='+str(d[0])
                        text="DMS ALert,click on %s "%(link)
                        sentSMS(phone[str(res)][0],text)
        except Exception as e:
            print(e)
    return True


#################### FUNCTIONS End ##################################

#################### Admin Start ###############################
@application.route("/admin", methods=['GET','POST'])                 
def admin_home():
    if g.admin:
        query="SELECT COUNT(*) FROM SERVICES WHERE service_type=1"
        detail=selection(query)
        if detail!=False:
            for d in detail:
                ambulance=d[0]
        query="SELECT COUNT(*) FROM SERVICES WHERE service_type=2"
        detail=selection(query)
        if detail!=False:
            for d in detail:
                police=d[0]    
        query="SELECT COUNT(*) FROM SERVICES WHERE service_type=3"
        detail=selection(query)
        if detail!=False:
            for d in detail:
                ff=d[0]    
        query="SELECT COUNT(*) FROM SERVICES WHERE service_type=4"
        detail=selection(query)
        if detail!=False:
            for d in detail:
                hospital=d[0]                                    
        return render_template('admin_home.html',ambulance=ambulance,police=police,ff=ff,hospital=hospital)        
    return redirect('/admin_login')  

@application.route("/admin_login", methods=['GET','POST'])                 
def admin_login():
    if g.admin:
       return redirect('/admin_home')  
    else:
        if request.method == 'POST':
            email=request.form['email']
            password=request.form['password']
            if email=='admin@gmail.com':
                if password=='admin123':
                    session['admin'] = "approved"
                    print('done')
                    return redirect('/admin') 
            return render_template('login.html',response='404',msg="INVALID CREDENTIALS")
        return render_template('login.html')

@application.route("/admin_addService", methods=['GET','POST'])                 
def admin_addService():
    if g.admin:
        if request.method=='POST':
            data=request.form
            coord=getcoordinates(data['place'])
            query="INSERT INTO 'SERVICES'(service_name,service_location,service_type,service_phone,service_geolocation) values('%s','%s','%s','%s','%s')"%(data['name'],data['place'],data['service'],data['phone'],coord)
            detail=inUP(query)
            if detail!=False:
                return render_template('admin_addService.html',response='200')  
            else:
                return render_template('admin_addService.html',response='404')  

        return render_template('admin_addService.html')        
    return redirect('/admin_login')  

@application.route("/admin_viewServices", methods=['GET','POST'])                 
def admin_viewServices():
    if g.admin:
        item=[]
        if request.method=='POST':
            id=request.form['service_id']
            query="DELETE FROM SERVICES WHERE service_id='%s'"%(id)
            inUP(query)
        query="SELECT service_id,service_name,service_type,service_location,service_phone FROM SERVICES"
        detail=selection(query)
        if detail!=False:
            for d in detail:
                if d[2]=='1':
                    type='Ambulance'
                elif d[2]=='2':
                    type='Police'
                elif d[2]=='3':
                    type='Fire and Rescue'
                elif d[2]=='4':
                    type='Hospital'

                x={
                    'service_id':d[0],
                    'service_name':d[1],
                    'service_type':type,
                    'service_location':d[3],
                    'service_phone':d[4]
                }
                item.append(x)
        return render_template('admin_viewServices.html',item=item)
    return redirect('/admin_login')     

@application.route("/admin_viewDetail", methods=['GET','POST'])                 
def admin_viewDetail():
    if g.admin:
        item=[]
        # query="SELECT DISASTER_MANGEMENT.dis_id,DISASTER_MANGEMENT.dis_ambulance,DISASTER_MANGEMENT.dis_police,DISASTER_MANGEMENT.dis_FF,DISASTER_MANGEMENT.dis_hosp,DISASTERS.dis_place,DISASTERS.dis_datetime FROM DISASTER_MANGEMENT INNER JOIN DISASTERS ORDER BY DISASTERS.dis_id DESC"
        query="SELECT dis_id,dis_ambulance,dis_police,dis_FF,dis_hosp FROM DISASTER_MANGEMENT WHERE dis_id  IN (SELECT dis_id FROM DISASTERS ORDER BY dis_id DESC)"
        if request.method=='POST':
            date=request.form['date']
            date=datetime.datetime.strptime(date,'%Y-%m-%d')
            date=date.strftime("%m/%d/%Y")
            # query="SELECT DISASTER_MANGEMENT.dis_id,DISASTER_MANGEMENT.dis_ambulance,DISASTER_MANGEMENT.dis_police,DISASTER_MANGEMENT.dis_FF,DISASTER_MANGEMENT.dis_hosp,DISASTERS.dis_place,DISASTERS.dis_datetime FROM DISASTER_MANGEMENT INNER JOIN DISASTERS WHERE DISASTERS.dis_datetime LIKE '%s' ORDER BY DISASTERS.dis_id DESC"%(str(date)+'%')
            query="SELECT dis_id,dis_ambulance,dis_police,dis_FF,dis_hosp FROM DISASTER_MANGEMENT WHERE dis_id  IN (SELECT dis_id FROM DISASTERS WHERE dis_datetime LIKE '%s' ORDER BY dis_id DESC)"%(str(date)+'%')
            print(query)
        detail=selection(query)
        if detail!=False:
            for d in detail:
                query="SELECT dis_place,dis_datetime FROM DISASTERS WHERE dis_id=%s"%(d[0]) 
                detail1=selection(query)
                if detail1!=False:
                    for d1 in detail1:
                        x={
                            'dis_place':d1[0],
                            'dis_datetime':d1[1],
                            'dis_ambulance':None,
                            'dis_police':None,
                            'dis_FF':None,
                            'dis_hospital':None
                        }
                for i in range(1,5):
                    query="SELECT service_location FROM SERVICES WHERE service_id='%s'"%(d[i])
                    detail1=selection(query)
                    if detail1!=False:
                        for d1 in detail1:
                            location=d1[0]
                    query="SELECT service_status,service_time FROM REQUESTS WHERE service_id='%s' and dis_id='%s'"%(d[i],d[0])
                    detail1=selection(query)
                    if detail1!=False:
                        for d1 in detail1:
                            if i==1:
                                clm='dis_ambulance'
                            elif i==2:
                                clm='dis_police'
                            elif i==3:
                                clm='dis_FF'
                            elif i==4:
                                clm='dis_hospital'
                            x[clm]={
                                "location":location,
                                'service_time':d1[1],
                                'service_status':d1[0]
                            }
                item.append(x)
        return render_template('admin_viewDisaster.html',item=item)
    return redirect('/admin_login')      

@application.route("/logout",methods=['GET','POST'])
def admin_logout():
    session['admin'] = None
    return redirect('/')  

#################### Admin end ##################################
#################### Agent Start #################################

@application.route('/send_ima')
def download_qn ():
    path = os.path.join('web/static/qn_pdf/', str(request.args.get('ex_id'))+'.pdf')
    return send_file(path, as_attachment=True)

###################### DATABASE ###################################

def inUP(query): #Insertion or Updation Queries
    try:
        connection = sqlite3.connect('database.db')       
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        connection.close()
        return True
    except Exception as e:
        print(e)
        return False

def selection(query):  #Selection Queries
    try:
        connection = sqlite3.connect('database.db')       # Connect to the database
        connection.row_factory = sqlite3.Row
        cursor =  connection.cursor()
        cursor.execute(query)
        connection.commit()
        rv = cursor.fetchall()
        connection.close()
        return rv
    except Exception as e:
        print(e)
        return False

####################### DATABASE END###################################
def getcoordinates(text):
    api_key = 'ge-16de3168aa4951f2'
    query = "https://api.geocode.earth/v1/search?" \
            "api_key="+api_key+"&"\
            "text="+text.replace(' ', '+')

    response = json.load(urllib.request.urlopen(query))
    return response['features'][0]['geometry']['coordinates']

def distancecalculator(x,y):
    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(float(x[0]))
    lon1 = radians(float(x[1]))
    lat2 = radians(float(y[0]))
    lon2 = radians(float(y[1]))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return(distance)

def sentSMS(number,text):
    url = "https://www.fast2sms.com/dev/bulkV2"
    # payload = "sender_id=FSTSMS&message='%s'&language=english&route=p&numbers=%s"%(text,number)
    headers = {
    'authorization': "1bGHmyeJW5BdFhrStD9RMkoa4CV3w8QYAInKTPvpg7xlOui6Zj5gMKDpfdzAQF3TSexnIEGibtU1CLXJ",
   'Content-Type': "application/x-www-form-urlencoded",
    'Cache-Control': "no-cache",
    }
    payload={
        "route" : "v3",
        "sender_id" : "FTWSMS",
        "message" : text,
        "language" : "english",
        "flash" : 0,
        "numbers" :number,
        }

    response = requests.request("POST", url, json=payload, data=payload, headers=headers)
    print(response.text)
    return(response.text)

if __name__ == "__main__":
    application.debug = True
    application.run(host='0.0.0.0',port=5500)


