import os, sqlite3, secrets, json, time
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
ROOT=Path(__file__).resolve().parent
DB=os.environ.get('JOILE_DB_PATH',str(ROOT/'joile_fizz_secure.db'))
app=Flask(__name__,static_folder=None)
app.secret_key=os.environ.get('JOILE_SECRET_KEY')
if not app.secret_key: raise RuntimeError('Set JOILE_SECRET_KEY in hosting environment to a long random secret.')
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE','1')=='1',PERMANENT_SESSION_LIFETIME=28800)
app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1)
ROLES={'Admin':{'*'},'Accountant':{'Home','Reports','Parties','Sales Invoices','Purchase Bills','Payment-Out','Expenses','Purchase Order','Purchase Return / Debit Note','Bank Accounts','Cash In Hand','Cheques','Loan Accounts'},'Sales':{'Home','Parties','Items','Sales Invoices','Delivery Challan'},'Stock/Warehouse':{'Home','Items','Delivery Challan','Stock Movements'},'Viewer':{'Home','Reports','Parties','Items','Sales Invoices'}}
def connect():
 c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP)');c.execute("CREATE TABLE IF NOT EXISTS appdata(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL DEFAULT '{}',version INTEGER NOT NULL DEFAULT 0,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)");c.execute("INSERT OR IGNORE INTO appdata(id,payload) VALUES(1,'{}')");c.commit();return c
def get_user():
 uid=session.get('uid')
 if not uid:return None
 c=connect();u=c.execute('SELECT id,username,role,active FROM users WHERE id=?',(uid,)).fetchone();c.close()
 return dict(u) if u and u['active'] else None
def auth(fn):
 @wraps(fn)
 def w(*a,**k):
  u=get_user()
  if not u:return jsonify(error='Authentication required'),401
  request.user=u;return fn(*a,**k)
 return w
def admin(fn):
 @wraps(fn)
 @auth
 def w(*a,**k):
  if request.user['role']!='Admin':return jsonify(error='Admin only'),403
  return fn(*a,**k)
 return w
@app.get('/')
def index():return send_from_directory(ROOT,'index.html')
@app.get('/api/health')
def health():return jsonify(ok=True,service='Joile Fizz backend')
@app.post('/api/setup')
def setup():
 c=connect()
 if c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']:
  c.close();return jsonify(error='Initial setup is already completed'),409
 b=request.get_json(silent=True) or {};name=str(b.get('username','')).strip();pw=str(b.get('password',''))
 if len(name)<3 or len(pw)<14:c.close();return jsonify(error='Username must be 3+ characters and password at least 14 characters'),400
 c.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(name,generate_password_hash(pw),'Admin'));c.commit();c.close();return jsonify(ok=True,message='Admin created; disable /api/setup after first use')
@app.post('/api/register')
def register():
 # Public self-registration creates a least-privilege Viewer account only.
 b=request.get_json(silent=True) or {};name=str(b.get('username','')).strip();pw=str(b.get('password',''))
 if len(name)<3 or len(name)>80 or len(pw)<14:
  return jsonify(error='Username must be 3–80 characters and password at least 14 characters'),400
 c=connect()
 try:
  c.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(name,generate_password_hash(pw),'Viewer'));c.commit()
 except sqlite3.IntegrityError:
  c.close();return jsonify(error='That username already exists'),409
 c.close();return jsonify(ok=True,message='Account created. You can now sign in.',role='Viewer'),201

@app.post('/api/login')
def login():
 b=request.get_json(silent=True) or {};c=connect();u=c.execute('SELECT * FROM users WHERE username=? AND active=1',(str(b.get('username','')).strip(),)).fetchone();c.close()
 if not u or not check_password_hash(u['password_hash'],str(b.get('password',''))):return jsonify(error='Invalid username or password'),401
 session.clear();session['uid']=u['id'];session.permanent=True
 return jsonify(ok=True,user={'username':u['username'],'role':u['role']})
@app.post('/api/logout')
def logout():session.clear();return jsonify(ok=True)
@app.get('/api/me')
@auth
def me():return jsonify(user=request.user,permissions=sorted(ROLES.get(request.user['role'],set())))
@app.get('/api/users')
@admin
def users():
 c=connect();rows=c.execute('SELECT id,username,role,active,created_at FROM users ORDER BY id').fetchall();c.close();return jsonify(users=[dict(x) for x in rows])
@app.post('/api/users')
@admin
def create_user():
 b=request.get_json(silent=True) or {};name=str(b.get('username','')).strip();pw=str(b.get('password',''));role=b.get('role')
 if len(name)<3 or len(pw)<14 or role not in ROLES or role=='Admin':return jsonify(error='Username 3+ chars, password 14+ chars, and a valid employee role required'),400
 c=connect()
 try:c.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(name,generate_password_hash(pw),role));c.commit()
 except sqlite3.IntegrityError:c.close();return jsonify(error='Username already exists'),409
 c.close();return jsonify(ok=True)
@app.patch('/api/users/<int:uid>')
@admin
def update_user(uid):
 b=request.get_json(silent=True) or {};c=connect();u=c.execute('SELECT role FROM users WHERE id=?',(uid,)).fetchone()
 if not u:c.close();return jsonify(error='User not found'),404
 if u['role']=='Admin':c.close();return jsonify(error='Admin accounts cannot be changed here'),400
 role=b.get('role',u['role']);active=1 if b.get('active',True) else 0
 if role not in ROLES or role=='Admin':c.close();return jsonify(error='Invalid role'),400
 c.execute('UPDATE users SET role=?,active=? WHERE id=?',(role,active,uid));c.commit();c.close();return jsonify(ok=True)
@app.get('/api/data')
@auth
def get_data():
 c=connect();r=c.execute('SELECT payload,version,updated_at FROM appdata WHERE id=1').fetchone();c.close();return jsonify(payload=json.loads(r['payload']),version=r['version'],updated_at=r['updated_at'])
@app.put('/api/data')
@auth
def put_data():
 if request.user['role']=='Viewer':return jsonify(error='Read-only role'),403
 b=request.get_json(silent=True) or {};p=b.get('payload');v=b.get('version')
 if not isinstance(p,dict) or v is None:return jsonify(error='payload object and current version required'),400
 c=connect();r=c.execute('SELECT version FROM appdata WHERE id=1').fetchone()
 if int(v)!=r['version']:c.close();return jsonify(error='Conflict: data changed elsewhere; reload before saving',version=r['version']),409
 c.execute('UPDATE appdata SET payload=?,version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=1',(json.dumps(p,separators=(',',':')),));c.commit();v=c.execute('SELECT version FROM appdata WHERE id=1').fetchone()['version'];c.close();return jsonify(ok=True,version=v)
@app.get('/api/permissions')
@auth
def permissions():return jsonify(role=request.user['role'],sections=sorted(ROLES.get(request.user['role'],set())))
if __name__=='__main__':
 with connect() as c: print('Database initialized at',DB)
 app.run(host='0.0.0.0',port=int(os.environ.get('PORT','8000')))
