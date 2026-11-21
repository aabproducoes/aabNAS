import os,json,time,secrets,hmac
from pathlib import Path
from functools import wraps
from flask import Flask,request,jsonify,send_file,abort
from werkzeug.utils import secure_filename

ROOT=Path(os.environ.get('NAS_MEDIA_ROOT','/volume1/Media')).resolve()
DATA=Path(os.environ.get('NAS_GALLERY_DATA',str(Path.home()/'.nas-gallery'))).resolve();DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'galleries.json';PASSWORD=os.environ.get('NAS_GALLERY_ADMIN_PASSWORD','');ORIGIN=os.environ.get('NAS_GALLERY_ORIGIN','https://YOUR-USERNAME.github.io')
IMAGES={'.jpg','.jpeg','.png','.gif','.webp','.bmp','.avif'};VIDEOS={'.mp4','.m4v','.webm','.mov','.mkv','.avi'};ALLOWED=IMAGES|VIDEOS
SESSIONS={};ATTEMPTS={};app=Flask(__name__)
DEFAULT={'settings':{'site_title':'Explore my world.','site_description':'A collection of images and videos, hosted on my NAS.','theme':'midnight','background_color':'#0d1320','background_image':''},'galleries':[]}
def dbread():
 if not DB.exists():dbwrite(DEFAULT)
 try:return json.loads(DB.read_text(encoding='utf-8'))
 except Exception:return DEFAULT.copy()
def dbwrite(d):
 t=DB.with_suffix('.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(DB)
def safe(rel):
 p=(ROOT/rel).resolve()
 if p!=ROOT and ROOT not in p.parents:abort(403)
 return p
def gallery(gid):return next((g for g in dbread()['galleries'] if g['id']==gid),None)
def folder(g):
 p=safe(g['folder'])
 if not p.is_dir():abort(404)
 return p
def file_for(g,rel):
 root=folder(g);p=(root/rel).resolve()
 if p!=root and root not in p.parents:abort(403)
 if not p.is_file() or p.suffix.lower() not in ALLOWED:abort(404)
 return p
@app.after_request
def cors(r):
 o=request.headers.get('Origin','')
 if o==ORIGIN:
  r.headers['Access-Control-Allow-Origin']=o;r.headers['Access-Control-Allow-Headers']='Content-Type, Authorization';r.headers['Access-Control-Allow-Methods']='GET, POST, PUT, DELETE, OPTIONS';r.headers['Vary']='Origin'
 r.headers['X-Content-Type-Options']='nosniff';r.headers['Cache-Control']='no-store';return r
@app.route('/',defaults={'path':''},methods=['OPTIONS'])
@app.route('/<path:path>',methods=['OPTIONS'])
def options(path):return '',204
def error(msg,code):return jsonify(error=msg),code
def admin(fn):
 @wraps(fn)
 def wrap(*a,**kw):
  h=request.headers.get('Authorization','');tok=h[7:] if h.startswith('Bearer ') else '';exp=SESSIONS.get(tok)
  if not exp or exp<time.time():SESSIONS.pop(tok,None);return error('Administrator login required.',401)
  return fn(*a,**kw)
 return wrap
@app.get('/api/settings')
def settings():return jsonify(dbread()['settings'])
@app.get('/api/galleries')
def public_galleries():
 out=[]
 for g in dbread()['galleries']:
  try:
   d=folder(g);cover=g.get('cover','')
   if cover:file_for(g,cover)
   else:cover=next((p.name for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMAGES),'')
   out.append({'id':g['id'],'title':g['title'],'description':g.get('description',''),'cover':cover})
  except (OSError,ValueError):continue
 return jsonify(galleries=out)
@app.get('/api/galleries/<gid>/items')
def items(gid):
 g=gallery(gid)
 if not g:abort(404)
 d=folder(g)
 try:off=max(0,int(request.args.get('offset',0)));lim=min(40,max(1,int(request.args.get('limit',40))))
 except ValueError:return error('Invalid pagination.',400)
 fs=sorted((p for p in d.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED and not p.name.startswith('.')),key=lambda p:p.name.lower())
 chosen=fs[off:off+lim];return jsonify(items=[{'name':p.name,'type':'image' if p.suffix.lower() in IMAGES else 'video','size':p.stat().st_size} for p in chosen],next_offset=(off+len(chosen) if off+len(chosen)<len(fs) else None),total=len(fs))
@app.get('/api/media/<gid>/<path:rel>')
def media(gid,rel):
 g=gallery(gid)
 if not g:abort(404)
 return send_file(file_for(g,rel),conditional=True,etag=True,max_age=300)
@app.post('/api/admin/login')
def login():
 if not PASSWORD:return error('NAS_GALLERY_ADMIN_PASSWORD is not configured.',503)
 ip=request.headers.get('CF-Connecting-IP',request.remote_addr or '?');now=time.time();recent=[t for t in ATTEMPTS.get(ip,[]) if now-t<900]
 if len(recent)>=8:return error('Too many attempts. Try again in 15 minutes.',429)
 pw=(request.get_json(silent=True) or {}).get('password','')
 if not hmac.compare_digest(str(pw),PASSWORD):recent.append(now);ATTEMPTS[ip]=recent;return error('Incorrect password.',401)
 ATTEMPTS.pop(ip,None);tok=secrets.token_urlsafe(36);SESSIONS[tok]=now+8*3600;return jsonify(token=tok,expires_in=28800)
@app.get('/api/admin/me')
@admin
def me():return jsonify(authenticated=True)
@app.get('/api/admin/galleries')
@admin
def admin_galleries():return jsonify(galleries=dbread()['galleries'])
@app.get('/api/admin/folders')
@admin
def folders():
 rel=request.args.get('path','');d=safe(rel)
 if not d.is_dir():abort(404)
 return jsonify(path=rel,folders=[{'name':p.name,'path':str(p.relative_to(ROOT))} for p in sorted(d.iterdir(),key=lambda x:x.name.lower()) if p.is_dir() and not p.name.startswith('.')])
@app.post('/api/admin/galleries')
@admin
def create_gallery():
 b=request.get_json(silent=True) or {};title=str(b.get('title','')).strip()[:80];desc=str(b.get('description','')).strip()[:300];rel=str(b.get('folder','')).strip();p=safe(rel)
 if not title or not rel or not p.is_dir() or p==ROOT:return error('Choose a title and a valid subfolder.',400)
 d=dbread()
 if any(x['folder']==rel for x in d['galleries']):return error('This folder is already assigned to a gallery.',409)
 g={'id':secrets.token_urlsafe(9).replace('-','').replace('_',''),'title':title,'description':desc,'folder':rel};d['galleries'].append(g);dbwrite(d);return jsonify(g),201
@app.put('/api/admin/galleries/<gid>')
@admin
def update_gallery(gid):
 b=request.get_json(silent=True) or {};d=dbread();g=next((x for x in d['galleries'] if x['id']==gid),None)
 if not g:abort(404)
 rel=str(b.get('folder','')).strip();p=safe(rel);title=str(b.get('title','')).strip()[:80]
 if not title or not p.is_dir() or p==ROOT:return error('Choose a title and valid subfolder.',400)
 if any(x['id']!=gid and x['folder']==rel for x in d['galleries']):return error('Folder already assigned.',409)
 g.update(title=title,description=str(b.get('description','')).strip()[:300],folder=rel);dbwrite(d);return jsonify(g)
@app.delete('/api/admin/galleries/<gid>')
@admin
def delete_gallery(gid):
 d=dbread();n=len(d['galleries']);d['galleries']=[g for g in d['galleries'] if g['id']!=gid]
 if len(d['galleries'])==n:abort(404)
 dbwrite(d);return jsonify(ok=True) # removes listing only, never deletes NAS folder
@app.put('/api/admin/settings')
@admin
def update_settings():
 b=request.get_json(silent=True) or {};d=dbread();s=d['settings'];theme=b.get('theme','midnight')
 if theme not in {'midnight','ocean','forest','sunset','light'}:return error('Invalid theme.',400)
 color=str(b.get('background_color',s['background_color']))
 if len(color)!=7 or not color.startswith('#'):return error('Invalid color.',400)
 image=str(b.get('background_image','')).strip()
 if image and not image.startswith('https://'):return error('Background image must use HTTPS.',400)
 s.update(site_title=str(b.get('site_title','')).strip()[:80],site_description=str(b.get('site_description','')).strip()[:180],theme=theme,background_color=color,background_image=image[:1000]);dbwrite(d);return jsonify(s)
@app.put('/api/admin/files/<gid>/<path:rel>')
@admin
def rename_file(gid,rel):
 g=gallery(gid)
 if not g:abort(404)
 old=file_for(g,rel);b=request.get_json(silent=True) or {};name=secure_filename(str(b.get('new_name','')).strip())
 if not name or Path(name).suffix.lower() not in ALLOWED:return error('Use a valid media filename including extension.',400)
 new=old.with_name(name)
 if new.exists():return error('A file with that name already exists.',409)
 old.rename(new);return jsonify(ok=True,name=name)
@app.delete('/api/admin/files/<gid>/<path:rel>')
@admin
def delete_file(gid,rel):
 g=gallery(gid)
 if not g:abort(404)
 file_for(g,rel).unlink();return jsonify(ok=True)
if __name__=='__main__':
 if not ROOT.exists():raise SystemExit(f'NAS_MEDIA_ROOT does not exist: {ROOT}')
 if not PASSWORD:raise SystemExit('Set NAS_GALLERY_ADMIN_PASSWORD before starting.')
 print(f'Public galleries use media root: {ROOT}');app.run(host='127.0.0.1',port=8765,threaded=True)
