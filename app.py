# app.py
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super-secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jogajog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ===== Database Models =====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(120), default="")
    bio = db.Column(db.String(300), default="")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='posts')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    username = db.Column(db.String(80))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== Helpers =====
def current_user():
    uid = session.get('user_id')
    if uid:
        return User.query.get(uid)
    return None

# ===== Templates =====
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>যোগাযোগ</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin:0; background:#f0f2f5;}
.topbar{height:60px; background:#1877f2; color:white; display:flex; align-items:center; padding:0 18px; font-weight:700;}
.topbar a{color:white; text-decoration:none; margin-left:12px;}
.container{display:flex; flex-wrap:wrap; justify-content:center; gap:20px; padding:18px;}
.left, .feed, .right{background:white; border-radius:10px; padding:12px; box-shadow:0 1px 3px rgba(0,0,0,0.1);}
.left, .right{width:250px;}
.feed{flex:1; min-width:300px;}
input, textarea{width:100%; padding:8px; margin:4px 0; border-radius:6px; border:1px solid #ddd; outline:none;}
button{background:#1877f2; color:white; border:none; border-radius:6px; padding:8px; cursor:pointer;}
.post-item{border-bottom:1px solid #f0f0f0; padding:8px 0;}
.chat-box{height:300px; display:flex; flex-direction:column;}
.messages{flex:1; overflow:auto; padding:4px;}
.msg{margin-bottom:6px;}
.msg .who{font-weight:600; margin-right:4px;}
</style>
</head>
<body>
<div class="topbar">
  যোগাযোগ
  {% if user %}
    <span style="margin-left:auto;">Hello, {{ user.username }} <a href="{{ url_for('logout') }}">Logout</a></span>
  {% else %}
    <span style="margin-left:auto;"><a href="{{ url_for('login') }}">Login</a> | <a href="{{ url_for('register') }}">Register</a></span>
  {% endif %}
</div>

<div class="container">
  <div class="left">
    {% if user %}
    <div><b>{{ user.full_name or user.username }}</b><br>{{ user.bio or 'No bio yet' }}</div>
    {% else %}
    <div>Please login to see profile info.</div>
    {% endif %}
  </div>

  <div class="feed">
    {% if user %}
    <textarea id="postContent" rows="3" placeholder="What's on your mind, {{ user.username }}?"></textarea>
    <button onclick="createPost()">Post</button>
    {% else %}
    <div>Login to post.</div>
    {% endif %}
    <div id="feedList"><small>Loading feed...</small></div>
  </div>

  <div class="right">
    <div class="chat-box">
      <div>Public Chat</div>
      <div id="messages" class="messages"></div>
      <input id="chatUser" placeholder="Your name" value="{{ user.username if user else '' }}">
      <input id="chatMessage" placeholder="Message">
      <button onclick="sendMessage()">Send</button>
    </div>
  </div>
</div>

<script>
async function loadPosts(){
  let res = await fetch('/get_posts');
  let data = await res.json();
  let container = document.getElementById('feedList');
  if(!data.posts.length){container.innerHTML='<small>No posts yet</small>';return;}
  let html = '';
  data.posts.forEach(p=>{html+=`<div class="post-item"><b>${p.username}</b>: ${p.content}<br><small>${p.created}</small></div>`});
  container.innerHTML=html;
}
function escapeHtml(t){if(!t)return '';return t.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');}
async function createPost(){
  const content=document.getElementById('postContent').value.trim();
  if(!content) return alert('Write something first.');
  await fetch('/post',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content})});
  document.getElementById('postContent').value='';
  loadPosts();
}

async function loadMessages(){
  let res = await fetch('/get_messages');
  let data = await res.json();
  let box = document.getElementById('messages');
  box.innerHTML='';
  data.messages.forEach(m=>{
    let div=document.createElement('div'); div.className='msg';
    div.innerHTML=`<span class="who">${escapeHtml(m.username)}</span>: ${escapeHtml(m.content)} <small>${m.created}</small>`;
    box.appendChild(div);
  });
  box.scrollTop = box.scrollHeight;
}
async function sendMessage(){
  const user=document.getElementById('chatUser').value.trim()||'Guest';
  const content=document.getElementById('chatMessage').value.trim();
  if(!content) return;
  await fetch('/send_message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user,content})});
  document.getElementById('chatMessage').value='';
  loadMessages();
}
loadPosts(); loadMessages(); setInterval(loadMessages,2500); setInterval(loadPosts,5000);
</script>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>যোগাযোগ | Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;background:#f0f2f5;}
.container{display:flex;justify-content:center;align-items:center;height:100vh;}
.login-box{background:white;padding:40px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.2);width:360px;}
h2{text-align:center;color:#1877f2;margin-bottom:20px;font-weight:700;}
input[type=text],input[type=password]{width:100%;padding:12px;margin:8px 0;border-radius:6px;border:1px solid #ddd;outline:none;font-size:15px;}
button{width:100%;padding:12px;margin-top:12px;background:#1877f2;color:white;border:none;border-radius:6px;font-size:16px;cursor:pointer;}
button:hover{background:#165ecf;}
.links{text-align:center;margin-top:15px;}
.links a{color:#1877f2;text-decoration:none;margin:0 5px;font-size:14px;}
.links a:hover{text-decoration:underline;}
</style>
</head>
<body>
<div class="container">
<div class="login-box">
<h2>যোগাযোগ</h2>
<form method="POST">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Log In</button>
</form>
<div class="links">
<a href="{{ url_for('register') }}">Create New Account</a> |
<a href="#">Forgot Password?</a>
</div>
</div>
</div>
</body>
</html>
"""

# ===== Routes =====
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        user=User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash,password):
            session['user_id']=user.id
            return redirect(url_for('home'))
        return "Invalid credentials",400
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        full_name=request.form.get('full_name','')
        if User.query.filter_by(username=username).first():
            return "Username exists",400
        u=User(username=username,password_hash=generate_password_hash(password),full_name=full_name)
        db.session.add(u); db.session.commit()
        return redirect(url_for('login'))
    return """
    <h2>Register</h2>
    <form method="POST">
    <input name="username" placeholder="Username" required><br><br>
    <input name="full_name" placeholder="Full Name"><br><br>
    <input type="password" name="password" placeholder="Password" required><br><br>
    <button>Register</button>
    </form>
    """

@app.route('/logout')
def logout():
    session.pop('user_id',None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    user=current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template_string(BASE_HTML,user=user)

# ===== API Endpoints =====
@app.route('/post', methods=['POST'])
def create_post():
    user=current_user()
    if not user: return "Login required",401
    data=request.get_json() or {}
    content=data.get('content','').strip()
    if not content: return "Empty post",400
    p=Post(user_id=user.id,content=content)
    db.session.add(p); db.session.commit()
    return "OK"

@app.route('/get_posts')
def get_posts():
    posts=Post.query.order_by(Post.created_at.desc()).limit(20).all()
    data=[{'username':p.user.username,'content':p.content,'created':p.created_at.strftime('%Y-%m-%d %H:%M')} for p in posts]
    return jsonify({'posts':data})

@app.route('/send_message', methods=['POST'])
def send_message():
    data=request.get_json() or {}
    user=current_user()
    username=data.get('user') or (user.username if user else 'Guest')
    content=data.get('content','').strip()
    if not content: return "Empty message",400
    m=Message(user_id=(user.id if user else None),username=username,content=content)
    db.session.add(m); db.session.commit()
    return "OK"

@app.route('/get_messages')
def get_messages():
    messages=Message.query.order_by(Message.created_at.asc()).limit(50).all()
    data=[{'username':m.username,'content':m.content,'created':m.created_at.strftime('%H:%M')} for m in messages]
    return jsonify({'messages':data})

# ===== Run =====
if __name__=='__main__':
    db.create_all()
    app.run(debug=True)
