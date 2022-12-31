import csv, sqlite3
import myfitnesspal
import locale
import time
import hashlib
import os
from django.shortcuts import render
from datetime import datetime, timedelta
from sqlite3 import Error
from flask import Flask, redirect, request, render_template, session, jsonify, json
from flask_session import Session

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DATABASE = r'health.db'

@app.errorhandler(404)
def page_not_found(e):
    return render_template('pages-404.html'), 404

@app.errorhandler(500)
def page_not_found(e):
    return render_template('pages-500.html'), 404

def list_workouts():
    with open('static/lists/workouts.csv') as csv_file:
        data = csv.reader(csv_file, delimiter=',')
        first_line = True
        l_workouts = []
        for row in data:
            if not first_line:
                l_workouts.append({
                "workout": row[0]
                })
            else:
                first_line = False
    
    return l_workouts

def list_activities():
    with open('static/lists/activities.csv') as csv_file:
        data = csv.reader(csv_file, delimiter=',')
        first_line = True
        l_activities = []
        for row in data:
            if not first_line:
                l_activities.append({
                "name": row[0]
                })
            else:
                first_line = False
    
    return l_activities

def create_connection(db_file):
    # Create a database connection to a SQLite database
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
        return d

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def register_user(conn, user):
    sql = '''INSERT INTO users(email, name, password) VALUES (?,?,?);'''
    cur = conn.cursor()
    cur.execute(sql, user)
    conn.commit()
    conn.close()
    print("Successfully registered new user")

def new_workout(entry):
        
    #Get workout information from form
    workout_name = entry.get("name")
    workout_log_date = entry.get("log_date")
    workout_duration = entry.get("duration")
    workout_exercises = entry.get("exercises")
    workout_volume = entry.get("volume")
    workout_calories = entry.get("calories")
    workout_saved = entry.get("saved")
    
    #Store in new variable
    new_workout = (session["email"], workout_name, workout_saved, workout_log_date, workout_duration, workout_exercises, workout_volume, workout_calories)
    sql = '''INSERT INTO workouts(user_email, name, saved_workout, log_date, duration, exercises, volume, calories) VALUES (?,?,?,?,?,?,?,?) '''
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    cur.execute(sql, new_workout)
    conn.commit()
    print("Successfully logged new workout")

def new_weight(entry):

    #Get weight information from form
    weight_log_date = entry.get("log-date")
    weight_weight = entry.get("weight")
    
    #Store in new variable
    new_weight = (session["email"], weight_log_date, weight_weight)
    sql = '''INSERT INTO weight(user_email, log_date, weight) VALUES (?,?,?) '''
    new_entry = (sql, new_weight)
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    cur.execute(sql, new_weight)
    conn.commit()
    print("Successfully logged new weight")

def new_goal(entry):

    #Get goal information from form
    calories = int(entry.get('calories'))
    carbs = int(calories/4 * (int(entry.get('carbPerc'))/100))
    protein = int(calories/4 * (int(entry.get('proteinPerc'))/100))
    fats = int(calories/8 * (int(entry.get('fatPerc'))/100))
    entry = str(datetime.now())
    
    #Store in new variable
    new_goal = (session["email"], entry, calories, carbs, protein, fats)
    sql = '''INSERT INTO goals(email, entry, calories, carbs, protein, fats) VALUES (?,?,?,?,?,?) '''
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    cur.execute(sql, new_goal)
    conn.commit()
    print("Successfully logged new goal")

def del_workout(id):
    sql = ''' DELETE FROM workouts WHERE id = ? '''
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    cur.execute(sql, id)
    conn.commit()
    print("Successfully delete workout")
    return redirect("/")

def add_account(conn, new_acct_info):
    sql = '''INSERT INTO accounts(user_email, account, acct_email, acct_password) VALUES (?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, new_acct_info)
    conn.commit()
    print("Saved account.")

def auth_mfp(email, password):
    client = myfitnesspal.Client(email, password)
    d = datetime.today()
    try:
        day = client.get_date(d.year, d.month, d.day)
        return 1
    except:
        return 0

def get_progress(user_email):
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    if cur.execute("SELECT EXISTS(SELECT acct_email FROM accounts WHERE user_email=? AND account=?)", (user_email,"MyFitnessPal",)).fetchone() == (1,):
        r = cur.execute("SELECT acct_email, acct_password FROM accounts WHERE user_email=? AND account=?", (user_email,"MyFitnessPal",)).fetchone()
        try:
            client = myfitnesspal.Client(r[0], password=r[1])
            d = datetime.today()
            macros = client.get_date(d.year, d.month, d.day)
            macros = macros.totals
            mfp_entry = ("MFP", session["email"], d, macros['calories'], macros['carbohydrates'], macros['protein'], macros['fat'])
            sql = '''INSERT INTO tracking(entry, email, entry_date, calories, carbs, protein, fats) VALUES (?,?,?,?,?,?,?) '''
            mfp_log = conn.cursor()
            mfp_log.execute(sql, mfp_entry)
            conn.commit()
            print("Saved MFP Entry")

            #Store last time was run
            sql = ''' INSERT INTO web_data(user_email, last_refresh) VALUES (?,?) '''
            last_accessed = (session["email"], datetime.now())
            mfp_save = conn.cursor()
            mfp_save.execute(sql, last_accessed)
            conn.commit()
            print("Stored last entry")
        except:
            print("Error connecting to MFP.")
    else:
        print("No account linked.")
    
def mfp_weight():
    conn = create_connection(DATABASE)
    cur = conn.cursor()

    try:
        r = cur.execute("SELECT acct_email, acct_password FROM accounts WHERE user_email = ? LIMIT 1", (session["email"],)).fetchone()
        client = myfitnesspal.Client(r[0], password=r[1])
    except:
        print("No accounts saved for the user", session["email"])
        return
    
    sql = ''' INSERT INTO weight(uid, user_email, log_date, weight) VALUES (?,?,?,?) '''
    load_weight = conn.cursor()

    try:
        weights = client.get_measurements("Weight")
    except:
        weights = ()
        print("Error connecting to MyFitnessPal.")
    
    if weights:
        for key, value in weights.items():
            entry = datetime.strftime(key, "%m-%d-%Y")
            uid = session["email"] + "-" + entry + "-" + str(value)
            new = (uid, session["email"], entry, value)
            try:
                load_weight.execute(sql, new)
            except:
                pass # UID match
        
        conn.commit()
        conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        if 'email' in session:
            
            con = sqlite3.connect("health.db")
            con.row_factory = sqlite3.Row

            try:    
                get_workouts = con.cursor()
                get_workouts.execute("select * from workouts order by 'log_date' ASC")
                workouts = get_workouts.fetchall();
            except:
                print("No workouts logged yet")
                workouts = {
                    'data': False,
                }

            try:
                get_workouts_chart = con.cursor()
                get_workouts_chart.execute("select saved_workout, round(avg(calories/duration)) as average_calories from workouts group by saved_workout order by average_calories DESC")
                sums = get_workouts_chart.fetchall();
            except:
                sums = {}

            # Get weights from MyFitnessPal and save to DB or just from DB if user has logged any
            mfp_weight()
            try:
                get_weights = con.cursor()
                get_weights.execute("SELECT * FROM weight WHERE user_email = ? ORDER BY log_date ASC LIMIT 15;", (session["email"],))
                weights = get_weights.fetchall();
            except:
                print("No weight logged yet")
                weights = {}
        
            try:
                web_data = con.cursor()
                FMT = '%Y-%m-%d %H:%M:%S.%f'
                lastRefresh = web_data.execute("select last_refresh from web_data order by id DESC LIMIT 1").fetchone()
                lastRefresh = lastRefresh[0]
                lastRefresh = datetime.strptime(lastRefresh, FMT)
                td = (datetime.now() - lastRefresh)
                minSinceRefresh = (td.seconds % 3600 // 60)
                lastRefresh = datetime.strftime(lastRefresh, "%m-%d-%Y %I:%M")
                if minSinceRefresh > 15:
                    get_progress(session["email"])

                get_macros = con.cursor()
                tdy = datetime.strftime(datetime.today(), "%Y-%m-%d")
                print(tdy)
                macro_sql = """ select calories, carbs, protein, fats from tracking where DATE(entry_date)=date('now') order by id DESC LIMIT 1"""
                macros = get_macros.execute(macro_sql).fetchone()
                macros = {'calories': macros[0], 'carbs': macros[1], 'protein': macros[2], 'fats': macros[3]}      
            except:
                print("No food entries")
                macros = {
                    'data': False,
                }
            
            try:
                get_goals = con.cursor()
                goals = get_goals.execute("select calories, carbs, protein, fats from goals order by id DESC LIMIT 1").fetchone()
                goals = {'calories': goals[0], 'carbs': goals[1], 'protein': goals[2], 'fats': goals[3]}
            except:
                print("No goals logged yet")
                goals = {}


            
            l_workouts = list_workouts()
            activities = list_activities()

            return render_template("dashboard-default.html", workouts=workouts, sums=sums, weights=weights, macros=macros, goals=goals, l_workouts=l_workouts, activities=activities)
        else:
            return render_template("index.html")
    else:
        id = request.form.get('id')
        del_workout(id)
        print("Workout " + id + " removed")
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route('/settings', methods=["POST", "GET"])
def settings():
    if request.method == "GET":
        
        con = sqlite3.connect("health.db")
        con.row_factory = sqlite3.Row
        
        try:
            get_mfp = con.cursor()
            mfp = get_mfp.execute("select acct_email from accounts order by id DESC LIMIT 1").fetchone()
            mfp = {'username': mfp[0]}
        except:
            print("No external accounts linked yet")
            mfp = {}

        return render_template("pages-settings.html", mfp=mfp)

    elif request.method == "POST":
        conn = create_connection(DATABASE)
        if request.form["submit_button"] == "mfp":
            auth_success = auth_mfp(request.form.get("inputEmailPal"), request.form.get("inputPasswordPal"))
            if auth_success == 1:
                new_acct_info = (session["email"], "MyFitnessPal", request.form.get("inputEmailPal"), request.form.get("inputPasswordPal"))
                add_account(conn, new_acct_info)
                return redirect("/settings#accounts")
            else:
                return redirect("pages-500.html")
        elif request.form["submit_button"] == "fitbod":
            new_acct_info = (session["email"], "Fitbod", request.form.get("inputEmailFit"), request.form.get("inputPasswordFit"))
            add_account(conn, new_acct_info)
        else:
            return "Not Working"

@app.route('/signout')
def signout():
    session["email"] = None
    return render_template("index.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":

        con = sqlite3.connect('health.db')
        con.row_factory = sqlite3.Row
        get_pass = con.cursor()
        password = get_pass.execute("SELECT password FROM users WHERE email = ?;", (request.form.get('email'),)).fetchone()
        password = password[0]

        salt = password[:32] # Get the salt
        key = password[32:] # Get the key
        new_key = hashlib.pbkdf2_hmac('sha256', request.form.get('password').encode('utf-8'), salt, 100000)

        if key == new_key:
            print('Login successful')
            return redirect("/")
        else:
            print('Passwords are not the same')
            return render_template("pages-sign-in.html")

    return render_template("pages-sign-in.html") # If error send back to the Login page

@app.route('/tracking', methods=["POST", "GET"])
def tracking():
    if request.method == "POST":
        
        if 'workouts' in request.form:
            new_workout(request.form)
        elif 'health' in request.form:
            new_weight(request.form)
        elif 'goal' in request.form:
            new_goal(request.form)
        else:
            new_food(request.form)
        
        return redirect("/")
    else:
        return render_template("tracking.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        
        sql_create_users_table = """ CREATE TABLE IF NOT EXISTS users (
                                        email text PRIMARY KEY,
                                        name text,
                                        password text
                                    );"""

        sql_create_web_data_table = """ CREATE TABLE IF NOT EXISTS web_data (
                                        id integer PRIMARY KEY,
                                        user_email text,
                                        last_refresh datetime
                                    ); """ 

        sql_create_tracking_table = """ CREATE TABLE IF NOT EXISTS tracking (
                                        id integer PRIMARY KEY,
                                        entry text,
                                        email text,
                                        entry_date date,
                                        calories integer,
                                        carbs integer,
                                        protein integer,
                                        fats integer 
                                    );"""

        sql_create_goals_table = """ CREATE TABLE IF NOT EXISTS goals (
                                        id integer PRIMARY KEY,
                                        email text,
                                        entry text,
                                        calories integer,
                                        carbs integer,
                                        protein integer,
                                        fats integer 
                                    );"""

        sql_create_accounts_table = """ CREATE TABLE IF NOT EXISTS accounts (
                                            id integer PRIMARY KEY,
                                            user_email text NOT NULL,
                                            account text NOT NULL,
                                            acct_email text NOT NULL,
                                            acct_password text NOT NULL
                                        );"""

        sql_create_workouts_table = """ CREATE TABLE IF NOT EXISTS workouts (
                                        id integer PRIMARY KEY,
                                        user_email text,
                                        name text,
                                        saved_workout text,
                                        log_date date,
                                        duration integer,
                                        exercises integer,
                                        volume integer,
                                        calories integer
                                    ); """
        
        sql_create_weight_table = """ CREATE TABLE IF NOT EXISTS weight (
                                        uid text primary key,
                                        user_email text,
                                        log_date date,
                                        weight real
                                    ); """

        sql_create_workout_list_table = """ CREATE TABLE IF NOT EXISTS workout_list (
                                            id integer primary key,
                                            workout text
                                        ); """

        conn = create_connection(DATABASE)
        if conn is not None:
            # Create tables
            create_table(conn, sql_create_users_table)
            create_table(conn, sql_create_accounts_table)
            create_table(conn, sql_create_goals_table)
            create_table(conn, sql_create_tracking_table)
            create_table(conn, sql_create_workouts_table)
            create_table(conn, sql_create_weight_table)
            create_table(conn, sql_create_workout_list_table)
            conn.commit()
        else:
            print("Error! Cannot create the database connection.")

        session["name"] = request.form.get("name")
        session["email"] = request.form.get("email")
        
        # Get email, name, and password from the form
        email = request.form.get("email")
        name = request.form.get("name")

        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', request.form.get("password").encode('utf-8'), salt, 100000)
        password = salt + key

        # Register the new user
        user = (email, name, password)
        conn = create_connection(DATABASE)
        register_user(conn, user)

        return redirect("/")
    else:
        return render_template("pages-sign-up.html")

@app.route('/main')
def main():
    return render_template("index.html")
    
@app.route('/signin')
def signin():
    return render_template("pages-sign-in.html")

if __name__ == "main":
    app.run(debug=True, host= '192.168.1.20')