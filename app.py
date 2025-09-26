# app.py
from flask import Flask, render_template_string, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "very-secret-key-change-this"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jogajog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ===== Models =====
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
    user_id = db.Column(db.Integer)  # sender user id
    username = db.Column(db.String(80))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== Helpers =====
def current_user():
    uid = session.get('user_id')
    if uid:
        return User.query.get(uid)
    return None

# ===== Templates (single-file) =====
BASE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>যোগাযোগ — Mini Social</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    /* Google-font-like feel without external load */
    :root{
      --blue:#1877f2; --muted:#65676b; --card:#fff;
      --bg:#f0f2f5; --glass: rgba(255,255,255,0.9);
    }
    html,body{height:100%; margin:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; background:var(--bg);}
    .topbar{height:60px; background:linear-gradient(90deg,var(--card), #e9eefc); display:flex; align-items:center; padding:0 18px; box-shadow: 0 1px 0 rgba(0,0,0,0.06);}
    .brand{color:var(--blue); font-weight:700; font-size:20px; margin-right:20px;}
    .search{flex:1; max-width:520px;}
    .search input{width:100%; padding:8px 12px; border-radius:18px; border:1px solid #ddd; outline:none;}
    .top-actions{display:flex; gap:8px; align-items:center;}
    .btn{background:var(--blue); color:white; padding:8px 12px; border-radius:6px; text-decoration:none;}
    .container{display:flex; gap:20px; padding:18px; max-width:1100px; margin:18px auto;}
    .left, .right{width:230px;}
    .card{background:var(--card); border-radius:10px; padding:12px; box-shadow:0 1px 3px rgba(0,0,0,0.06); margin-bottom:12px;}
    .profile-pic{width:48px; height:48px; border-radius:50%; background:linear-gradient(135deg,#6b8cff,#b6d8ff); display:inline-block; vertical-align:middle; margin-right:10px;}
    .feed{flex:1; min-width:0;}
    .post-box textarea{width:100%; border:0; resize:none; outline:none; font-size:15px; background:transparent;}
    .post-btn{float:right; margin-top:8px;}
    .post-item{padding:12px; border-bottom:1px solid #f0f0f0;}
    .post-meta{color:var(--muted); font-size:13px; margin-bottom:8px;}
    .chat-box{height:400px; display:flex; flex-direction:column;}
    .messages{flex:1; overflow:auto; padding:8px;}
    .msg{margin-bottom:8px;}
    .msg .who{font-weight:600; margin-right:8px;}
    .chat-input{display:flex; gap:8px; padding-top:8px;}
    .chat-input input{flex:1; padding:8px; border-radius:8px; border:1px solid #ddd; outline:none;}
    .small{font-size:13px; color:var(--muted);}
    a { color: inherit; text-decoration: none;}
    /* responsive */
    @media(max-width:900px){
      .left, .right{display:none;}
      .container{padding:12px;}
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="brand">যোগাযোগ</div>
    <div class="search"><input placeholder="Search (username)..." id="globalSearch"></div>
    <div class="top-actions">
      {% if user %}
        <div class="small">Hello, {{ user.username }}</div>
        <a class="btn" href="{{ url_for('logout') }}">Logout</a>
      {% else %}
        <a class="btn" href="{{ url_for('login') }}">Login</a>
      {% endif %}
    </div>
  </div>

  <div class="container">
    <div class="left">
      <div class="card">
        {% if user %}
          <div style="display:flex; align-items:center;">
            <div class="profile-pic"></div>
            <div>
              <div style="font-weight:700;">{{ user.full_name or user.username }}</div>
              <div class="small">{{ user.bio or "No bio yet" }}</div>
            </div>
          </div>
        {% else %}
          <div style="text-align:center;">
            <p><b>যোগাযোগ</b> এ লগইন করে বন্ধুদের সাথে যোগাযগ করো।</p>
            <a href="{{ url_for('register') }}">Register</a> · <a href="{{ url_for('login') }}">Login</a>
          </div>
        {% endif %}
      </div>

      <div class="card">
        <div style="font-weight:700; margin-bottom:8px;">Explore</div>
        <div class="small">Profile · Friends · Marketplace · Groups</div>
      </div>
    </div>

    <div class="feed">
      <div class="card post-box">
        {% if user %}
          <div style="display:flex; gap:10px; align-items:flex-start;">
            <div class="profile-pic"></div>
            <div style="flex:1;">
              <textarea id="postContent" rows="3" placeholder="What's on your mind, {{ user.username }}?"></textarea>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div class="small">You can post text only</div>
                <button class="btn post-btn" onclick="createPost()">Post</button>
              </div>
            </div>
          </div>
        {% else %}
          <div style="text-align:center;">
            <a class="btn" href="{{ url_for('login') }}">Login to Post</a>
          </div>
        {% endif %}
      </div>

      <div id="feedList" class="card">
        <!-- posts loaded with JS -->
        <div class="small" id="loadingPosts">Loading feed...</div>
      </div>
    </div>

    <div class="right">
      <div class="card">
        <div style="font-weight:700; margin-bottom:8px;">Contacts</div>
        <div class="small">Online friends will appear here</div>
      </div>

      <div class="card chat-box">
        <div style="font-weight:700; margin-bottom:8px;">Public Chat</div>
        <div id="messages" class="messages"></div>
        <div class="chat-input">
          <input id="chatUser" placeholder="Your name" value="{{ user.username if user else '' }}">
          <input id="chatMessage" placeholder="Message...">
          <button class="btn" onclick="sendMessage()">Send</button>
        </div>
      </div>
    </div>
  </div>

<script>
  // Load posts
  async function loadPosts(){
    document.getElementById('loadingPosts').textContent = 'Loading feed...';
    let res = await fetch('/get_posts');
    let data = await res.json();
    let container = document.getElementById('feedList');
    if(!data.posts.length){
      container.innerHTML = '<div class="small">No posts yet — be the first!</div>';
      return;
    }
    let html = '';
    data.posts.forEach(p => {
      html += `<div class="post-item">
                <div class="post-meta"><b>${escapeHtml(p.username)}</b> · <span class="small">${p.created}</span></div>
                <div>${escapeHtml(p.content)}</div>
               </div>`;
    });
    container.innerHTML = html;
  }

  function escapeHtml(text){ if(!text) return ''; return text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }

  async function createPost(){
    const content = document.getElementById('postContent').value.trim();
    if(!content) return alert('Write something first.');
    await fetch('/post', {
      method:'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({content})
    });
    document.getElementById('postContent').value = '';
    loadPosts();
  }

  // Chat functions (polling)
  async function loadMessages(){
    let res = await fetch('/get_messages');
    let data = await res.json();
    let box = document.getElementById('messages');
    box.innerHTML = '';
    data.messages.forEach(m => {
      let div = document.createElement('div');
      div.className = 'msg';
      div.innerHTML = `<span class="who">${escapeHtml(m.username)}</span><span class="small">${m.created}</span><div>${escapeHtml(m.content)}</div>`;
      box.appendChild(div);
    });
    box.scrollTop = box.scrollHeight;
  }

  async function sendMessage(){
    const user = document.getElementById('chatUser').value.trim() || 'Guest';
    const content = document.getElementById('chatMessage').value.trim();
    if(!content) return;
    await fetch('/send_message', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({user, content})
    });
    document.getElementById('chatMessage').value = '';
    loadMessages();
  }

  // Kick off
  loadPosts();
  loadMessages();
  setInterval(loadMessages, 2500); // poll every 2.5s
  setInterval(loadPosts, 5000); // refresh feed every 5s
</script>
</body>
</html>
"""

# ===== Routes =====
@app.route('/')
def index():
    user = current_user()
    return render_template_string(BASE_HTML, user=user)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        full_name = request.form.get('full_name','').strip()
        if not username or not password:
            return "Username and password required", 400
        if User.query.filter_by(username=username).first():
            return "Username already exists", 400
        u = User(username=username, password_hash=generate_password_hash(password), full_name=full_name)
        db.session.add(u); db.session.commit()
        return redirect(url_for('login'))
    return render_template_string("""
    <h2>Register</h2>
    <form method="post">
      <input name="username" placeholder="username" required><br><br>
      <input name="full_name" placeholder="Full name"><br><br>
      <input name="password" type="password" placeholder="password" required><br><br>
      <button>Register</button>
    </form>
    <p><a href="{{ url_for('login') }}">Login</a></p>
    """)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        u = User.query.filter_by(username=username).first()
        if not u or not check_password_hash(u.password_hash, password):
            return "Invalid credentials", 400
        session['user_id'] = u.id
        return redirect(url_for('index'))
    return render_template_string("""
    <h2>Login</h2>
    <form method="post">
      <input name="username" placeholder="username" required><br><br>
      <input name="password" type="password" placeholder="password" required><br><br>
      <button>Login</button>
    </form>
    <p><a href="{{ url_for('register') }}">Register</a></p>
    """)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/post', methods=['POST'])
def create_post():
    user = current_user()
    if not user:
        return "Login required", 401
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return "Empty content", 400
    p = Post(user_id=user.id, content=content)
    db.session.add(p); db.session.commit()
    return jsonify({"ok": True})

@app.route('/get_posts')
def get_posts():
    posts = Post.query.order_by(Post.created_at.desc()).limit(50).all()
    data = []
    for p in posts:
        data.append({
            "id": p.id,
            "username": p.user.username,
            "content": p.content,
            "created": p.created_at.strftime("%b %d, %H:%M")
        })
    return jsonify({"posts": data})

# Chat endpoints (polling)
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json() or {}
    username = (data.get('user') or 'Guest')[:80]
    content = (data.get('content') or '').strip()
    if not content:
        return "Empty", 400
    m = Message(user_id = session.get('user_id') or 0, username=username, content=content)
    db.session.add(m); db.session.commit()
    return jsonify({"ok": True})

@app.route('/get_messages')
def get_messages():
    msgs = Message.query.order_by(Message.created_at.desc()).limit(100).all()
    msgs.reverse()
    data = []
    for m in msgs:
        data.append({
            "id": m.id,
            "username": m.username,
            "content": m.content,
            "created": m.created_at.strftime("%H:%M:%S")
        })
    return jsonify({"messages": data})

# ===== Run =====
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
