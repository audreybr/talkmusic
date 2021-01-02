# Meng-import library
from flask import Flask, redirect, url_for, session, request,jsonify,render_template, jsonify, make_response
from authlib.integrations.flask_client import OAuth
import os
import time
from datetime import timedelta
from functools import wraps

# Konfigurasi App, debugger untuk merapikan json dan auto reload .py saat ada perubahan
app = Flask(__name__)
app.config['DEBUG'] = True

# Konfigurasi session
app.secret_key = "secretkey"
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# oAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id="67521804560-k61l2jm3u13i6orjt1ucfh80qed4oonu.apps.googleusercontent.com",
    client_secret="aYLMVROLsyai16MW5xYhhVbk",
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only needed if using openId to fetch user info
    client_kwargs={'scope': 'openid email profile'},
)

# Koneksi ke MySQL
from flaskext.mysql import MySQL
import pymysql

mysql = MySQL()
app.secret_key = 'secretkey'
app.config['MYSQL_DATABASE_USER'] = 'rAsCELs8Of'
app.config['MYSQL_DATABASE_PASSWORD'] = 'kag5uKYDb3'
app.config['MYSQL_DATABASE_DB'] = 'rAsCELs8Of'
app.config['MYSQL_DATABASE_HOST'] = 'remotemysql.com'
app.config['MYSQL_DATABASE_PORT'] = 3306

mysql.init_app(app)

# Function untuk membuat response dari request
def ok(method,values,message):
    res = {
        'method' : method,
        'status' : 200,
        'desc' : "OK",
        'values' : values,
        'messages' : message
    }
    return make_response(jsonify(res))

def bad(method,values,message):
    res = {
        'method' : method,
        'status' : 400,
        'desc' : "Bad Request",
        'values' : values,
        'messages' : message
    }
    return make_response(jsonify(res))

# ROUTE UNTUK ME-RETURN HTML
# DAPAT DITEST MENGGUNAKAN BROWSER

# Function untuk mengarahkan ke login bila sudah berakhir
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = dict(session).get('profile', None)
        if user:
            return f(*args, **kwargs)

        return redirect(url_for('login'))
    return decorated_function

# Landing Page
@app.route('/')
def hello_world():
    return render_template('landing.html')

# Login page
# ketika button login ditekan
@app.route('/login')
def login():
    google = oauth.create_client('google')  # Membuat client Google oAuth
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')

# Authorization page
# redirect ke home page
@app.route('/authorized')
def authorize():
    google = oauth.create_client('google')  # Membuat client Google oAuth
    token = google.authorize_access_token()  # Mengakses token dari Google untuk mendapatkan email
    resp = google.get('userinfo')
    user_info = resp.json()
    user = oauth.google.userinfo() 
    session['profile'] = user_info
    session.permanent = True
    return redirect('/home')

# Home page
# saat pengguna sudah login
# langsung dapat melihat status dari berbagai orang yang menggunakan web
@app.route('/home', methods = ['GET'])
@login_required
def display_status():
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM status")
    rows = cursor.fetchall()

    result=[]
    for message in rows:
        message_call = {
            'statusid': message[0],
            'statusdetails': message[1]
        }
        result.append(message_call)
    conn.commit()
    conn.close()
    cursor.close()

    done = mysql.connect()
    cur = done.cursor()
    cur.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("GET", 200, "OK"))
    done.commit()
    return render_template("homepage.html",data=rows)

# Mengubah satu record data menjadi API
def single_transform(data):
    api_single_data = {
        'statusid' : data[0],
        'statusdetails' : data[1],
        'email' : data[2]
    }
    return api_single_data

# Menggabungkan record-record menjadi API
def transform(data):
    array = []
    for i in data:
        array.append(single_transform(i))
    return array

# My Status Page, untuk mengorganisir status seperti melihat, menambah, mengedit, maupun menghapus status
@app.route('/mystatus', methods=['GET','POST','PUT','DELETE'])
@login_required
def organize():
    if request.method == "GET":
        return view_status()
    elif request.method == "POST":
        return create_status()
    elif request.method == "PUT":
        return edit_status()
    elif request.method == "DELETE":
        return delete_status()

# function untuk melihat status user
def view_status():
    email = dict(session)['profile']['email']
    emailstr = {email}
    conn = mysql.connect()
    cursor = conn.cursor()
    sql = "SELECT * FROM status WHERE email = %s"
    cursor.execute(sql,{email})
    data = cursor.fetchall()
    conn.commit()
    conn.close()
    cursor.close()

    done = mysql.connect()
    cur = done.cursor()
    cur.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("GET", 200, "OK"))
    done.commit()
    return render_template('organize.html',data=data)

# function untuk menambah status
def create_status():
    #masukin db
    conn = mysql.connect()
    cursor = conn.cursor()

    email = dict(session)['profile']['email']
    statusdetails = request.form['statusdetails']

    query = 'INSERT INTO status (email, statusdetails) VALUES (%s, %s)'
    data = (email, statusdetails)
    cursor.execute(query,data)
    conn.commit()

    cursor.close()
    conn.close()

    done = mysql.connect()
    cur = done.cursor()
    cur.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("POST", 200, "OK"))
    done.commit()
    return render_template("organize.html")

# function untuk menghapus status
def delete_status():
    conn = mysql.connect()
    cursor = conn.cursor()
    email = dict(session)['profile']['email']
    statid = request.form['id']

    sql = "DELETE FROM status WHERE statusid = %s"
    data = statid
    
    sqlcek = "SELECT email FROM status WHERE statusid = %s"
    cursor.execute(sqlcek,data)
    a=cursor.fetchone()
    
    if a is None:
        cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("DELETE", 400, "Bad Request"))
        conn.commit()
    else:
        cursor.execute(sqlcek,data)
        b=cursor.fetchone()[0]
        if email == b:
            cursor.execute(sql,data)
            conn.commit()
            cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("DELETE", 200, "OK"))
            conn.commit()

    cursor.close()
    conn.close()
    return render_template("organize.html")

# function untuk mengedit status
def edit_status():
    email = dict(session)['profile']['email']
    statid = request.form['id']
    statusdetails = request.form['statusedited']

    conn = mysql.connect()
    cursor = conn.cursor()

    query = 'UPDATE status SET statusdetails = %s WHERE statusid = %s'
    data=(statusdetails,statid)

    sqlcek = "SELECT email FROM status WHERE statusid = %s"
    cursor.execute(sqlcek,statid)
    a=cursor.fetchone()
    
    if a is None:
        cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("PUT", 400, "Bad Request"))
        conn.commit()
    else:
        cursor.execute(sqlcek,statid)
        b=cursor.fetchone()[0]
        if email == b:
            cursor.execute(query,data)
            conn.commit()
            cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("PUT", 200, "OK"))
            conn.commit()

    cursor.close()
    conn.close()

    return render_template("organize.html")

# ROUTE UNTUK ME-RETURN JSON
# DAPAT DITEST MENGGUNAKAN POSTMAN
# dengan melakukan login terlebih dulu di 127.0.0.1/5000
# kemudian menekan F12, mengambil cookies di bagian application -> cookies, bagian google-login-session
# dan menambahkan cookies ini di header postman

# Function untuk mengarahkan ke login bila sudah berakhir
def login_required_api(f):
    @wraps(f)
    def decorated_function_api(*args, **kwargs):
        user = dict(session).get('profile', None)

        if user:
            return f(*args, **kwargs)

        return redirect(url_for('login_api'))
    return decorated_function_api

# Landing Page
@app.route('/api')
def hello_world_api():
    return render_template('landingapi.html')

# Login page
# ketika button login ditekan@app.route('/login/api')
@app.route('/login/api')
def login_api():
    google = oauth.create_client('google')  # Membuat client Google oAuth
    redirect_uri = url_for('authorize_api', _external=True)
    return google.authorize_redirect(redirect_uri)

# Authorization page
# redirect ke home page
@app.route('/authorized/api')
def authorize_api():
    google = oauth.create_client('google')  # Membuat client Google oAuth
    token = google.authorize_access_token()  # Mengakses token dari Google untuk mendapatkan email
    resp = google.get('userinfo')
    user_info = resp.json()
    user = oauth.google.userinfo() 
    session['profile'] = user_info
    session.permanent = True
    return redirect('/home/api')

# Home page
# saat pengguna sudah login
# menampilkan operasi yang mungkin
@app.route('/home/api', methods = ['GET'])
def display_all_api():
    done = mysql.connect()
    cur = done.cursor()
    cur.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("GET", 200, "OK"))
    done.commit()
    return render_template('homeapi.html')

# All status page
# Me-return seluruh status dari berbagai user dalam bentuk JSON
# Muncul bila ditekan tombol 'See all status'
@app.route('/allstatus/api', methods = ['GET'])
def display_status_api():
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM status")
    rows = cursor.fetchall()
    rows_api = transform(rows)
    conn.commit()
    conn.close()
    cursor.close()
    done = mysql.connect()
    cur = done.cursor()
    cur.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("GET", 200, "OK"))
    done.commit()
    if (rows_api == []):
        return (ok("GET", rows_api, "No status available!"))
    else:
        return (ok("GET", rows_api, "Status from around the world!"))

# My status page
# ada berbagai method
# setiap method memiliki return JSON yang berbeda dan dapat ditest di Postman dengan langkah yang telah dijelaskan di atas
# namun di browser hanya dapat dilihat hasil return dari method GET yang dilakukan dengan menekan 'See my status'
@app.route('/mystatus/api', methods=['GET','POST','PUT','DELETE'])
@login_required
def organize_api():
    if request.method == "GET":
        return view_status_api()
    elif request.method == "POST":
        return create_status_api()
    elif request.method == "PUT":
        return edit_status_api()
    elif request.method == "DELETE":
        return delete_status_api()

# Method GET
# Mengembalikan daftar status dalam bentuk JSON
def view_status_api():
    email = dict(session)['profile']['email']
    conn = mysql.connect()
    cursor = conn.cursor()
    sql = "SELECT * FROM status WHERE email = %s"
    cursor.execute(sql,{email})
    data = cursor.fetchall()
    rows_api = transform(data)
    conn.commit()
    conn.close()
    cursor.close()

    done = mysql.connect()
    cur = done.cursor()
    cur.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("GET", 200, "OK"))
    done.commit()

    if (rows_api == []):
        return (ok("GET", rows_api, "No status available!"))
    else:
        return (ok("GET", rows_api, "Status from you"))
    
# Method POST
def create_status_api():
    #masukin db
    conn = mysql.connect()
    cur1 = conn.cursor()
    email = dict(session)['profile']['email']

    statusdetails = request.form['statusdetails']

    query = 'INSERT INTO status (email, statusdetails) VALUES (%s, %s)'
    data = (email, statusdetails)
    cur1.execute(query,data)
    conn.commit()
    
    done = mysql.connect()
    cur = done.cursor()
    cur.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("POST", 200, "OK"))
    done.commit()
    return (ok("POST", '', "Your status: " + str(statusdetails) + ", has been submitted!"))

# Method DELETE
def delete_status_api():
    conn = mysql.connect()
    cursor = conn.cursor()
    email = dict(session)['profile']['email']
    statid = request.form['id']

    sql = "DELETE FROM status WHERE statusid = %s"
    data = statid

    sqlcek = "SELECT email FROM status WHERE statusid = %s"
    cursor.execute(sqlcek,data)
    a=cursor.fetchone()
    
    if a is None:
        cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("DELETE", 400, "Bad Request"))
        conn.commit()
        return (bad("DELETE", '', "Your status ID: " + str(statid) + ", is not available"))
    else:
        cursor.execute(sqlcek,data)
        b=cursor.fetchone()[0]
        if email == b:
            cursor.execute(sql,data)
            conn.commit()
            cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("DELETE", 200, "OK"))
            conn.commit()
            return (ok("DELETE", '', "Your status ID: " + str(statid) + ", has been deleted!"))    

    cursor.close()
    conn.close()

# Method PUT
def edit_status_api():
    email = dict(session)['profile']['email']
    statid = request.form['id']
    statusdetails = request.form['statusedited']

    conn = mysql.connect()
    cursor = conn.cursor()

    query = 'UPDATE status SET statusdetails = %s WHERE statusid = %s'
    data=(statusdetails,statid)

    sqlcek = "SELECT email FROM status WHERE statusid = %s"
    cursor.execute(sqlcek,statid)
    a=cursor.fetchone()
    
    if a is None:
        cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("PUT", 400, "Bad Request"))
        conn.commit()
        return (bad("PUT", '', "Your status ID: " + str(statid) + " edit request has failed"))
    else:
        cursor.execute(sqlcek,statid)
        b=cursor.fetchone()[0]
        if email == b:
            cursor.execute(query,data)
            conn.commit()
            cursor.execute("INSERT INTO log(log_method,status,message) VALUES (%s,%s,%s)", ("PUT", 200, "OK"))
            conn.commit()
            return (ok("PUT", '', "Your status ID: " + str(statid) + ", has been edited to: " + str(statusdetails)))

    cursor.close()
    conn.close()

# Logout page
# ketika button logout ditekan
# redirect ke landing page
@app.route('/logout/api')
def logout_api():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/api')


#Error Handler 404 not found, tidak ada endpoints    
@app.errorhandler(404)
def not_found(error=None):
    message = {
        'status': 404,
        'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0')