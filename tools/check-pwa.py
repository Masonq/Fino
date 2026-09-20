#!/usr/bin/env python3
"""
Проверка приложения, добавленного на домашний экран.

В таком режиме нет адресной строки браузера: сверху сразу часы и
вырез, снизу — полоска жеста «домой». Отступы под них задаёт система
через env(safe-area-inset-*), и на обычном мониторе они равны нулю —
поэтому в браузере всё выглядит ровно, а на телефоне содержимое лезет
под часы и под полоску.

Здесь эти поля подменяются вручную (59 сверху, 34 снизу — iPhone с
вырезом): в styles.css они читаются через переменные --sat/--sab
именно для того, чтобы их можно было подставить снаружи.

Проверяется две вещи: не стоит ли что-нибудь в зоне часов и не
прячется ли конец страницы под нижней панелью.

Запуск:  python3 tools/check-pwa.py
Нужна поднятая локальная база (как для tools/check-browser.py).
"""
import json, os, subprocess, sys, time, urllib.request
from playwright.sync_api import sync_playwright
ROOT="/home/claude/plonk"; API=8560; WEB=5606
ids=json.load(open('/tmp/ids.json')); TOKEN=ids["token"]
env={**os.environ,"DATABASE_URL":"postgresql://plonk:plonk@127.0.0.1/plonk","SECRET_KEY":"x","MEDIA_DIR":"/tmp/plonk-media"}
open(f"{ROOT}/frontend/vite.pwa.mjs","w").write("""import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ plugins:[react()], server:{ port:%d, host:'127.0.0.1', proxy:{'/api':'http://127.0.0.1:%d','/media':'http://127.0.0.1:%d'} } })
"""%(WEB,API,API))
subprocess.run("service postgresql start",shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
pr=[subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(API)],cwd=f"{ROOT}/backend",env=env,stdout=open('/tmp/api4.log','w'),stderr=subprocess.STDOUT),
    subprocess.Popen(["npx","vite","--config","vite.pwa.mjs"],cwd=f"{ROOT}/frontend",env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)]
def wait(u):
    for _ in range(80):
        try: urllib.request.urlopen(u,timeout=2); return True
        except Exception: time.sleep(.5)
    return False
SAT, SAB = 59, 34      # iPhone с вырезом: статус-бар 59, домашняя полоска 34
CHECK = """([sat, sab]) => {
  const out=[]; const H=innerHeight;
  const nav=document.querySelector('.bottomnav');
  const navTop = nav ? nav.getBoundingClientRect().top : H;
  // 1) верх: что-то стоит в зоне часов
  for (const e of document.querySelectorAll('button, a, input, h1, h2, .page-header, .card, .listing-card')) {
    const cs=getComputedStyle(e);
    if (cs.display==='none'||cs.visibility==='hidden'||+cs.opacity===0) continue;
    const r=e.getBoundingClientRect();
    if (r.width<10||r.height<10||r.top<-200) continue;
    if (r.top < sat && r.bottom > 4) {
      const name=e.tagName.toLowerCase()+(typeof e.className==='string'&&e.className?'.'+e.className.trim().split(/\\s+/)[0]:'');
      out.push('под часами: '+name+' верх '+Math.round(r.top)+' «'+(e.textContent||'').trim().slice(0,20)+'»');
    }
  }
  // 2) низ: докручиваем до конца и смотрим, не спрятал ли нав последнее
  window.scrollTo(0, document.body.scrollHeight);
  const doc=document.scrollingElement;
  const atBottom = doc.scrollHeight - doc.scrollTop - doc.clientHeight < 4;
  let worst=null;
  for (const e of document.querySelectorAll('button, a, input, p, h2, .listing-card, .profile-row')) {
    const cs=getComputedStyle(e);
    if (cs.display==='none'||cs.position==='fixed'||+cs.opacity===0) continue;
    if (nav && nav.contains(e)) continue;
    const r=e.getBoundingClientRect();
    if (r.width<10||r.height<10||r.bottom<0||r.top>H) continue;
    const hidden = r.bottom - navTop;      // насколько ушло под нижнюю панель
    if (hidden > 2 && (!worst || hidden>worst.hidden))
      worst={name:e.tagName.toLowerCase()+(typeof e.className==='string'&&e.className?'.'+e.className.trim().split(/\\s+/)[0]:''),
             hidden:Math.round(hidden), text:(e.textContent||'').trim().slice(0,22)};
  }
  if (atBottom && worst) out.push('конец страницы прячется под нижней панелью на '+worst.hidden+' точек: '+worst.name+' «'+worst.text+'»');
  return [...new Set(out)].slice(0,6);
}"""
try:
    assert wait(f"http://127.0.0.1:{API}/api/health") and wait(f"http://127.0.0.1:{WEB}/")
    mine=ids.get("listing")
    routes=["/","/search?q=a","/categories","/c/auto","/post","/favorites","/chats","/notifications",
            "/profile","/profile/edit","/saved","/history","/my",f"/go/{mine}","/support","/moderation",
            "/admin/users","/admin/stats","/login","/reviews/waiting","/rules"]
    try:
        cid=json.load(open('/tmp/chat.json'))['cid']; routes.append(f"/chat/{cid}")
    except Exception: pass
    with sync_playwright() as p:
        b=p.chromium.launch()
        c=b.new_context(viewport={"width":390,"height":844},device_scale_factor=2,locale="ru-RU")
        c.add_init_script(f"localStorage.setItem('plonk_token','{TOKEN}');localStorage.setItem('i18nextLng','ru')")
        # подменяем безопасные поля: так ведёт себя приложение с домашнего экрана
        c.add_init_script(f"""document.addEventListener('DOMContentLoaded',()=>{{
            document.documentElement.style.setProperty('--sat','{SAT}px');
            document.documentElement.style.setProperty('--sab','{SAB}px');}})""")
        bad=0
        for rt in routes:
            pg=c.new_page(); pg.goto(f"http://127.0.0.1:{WEB}{rt}"); pg.wait_for_timeout(1800)
            found=pg.evaluate(CHECK, [SAT, SAB])
            extra=pg.evaluate("""([sat,sab])=>{const out=[];const H=innerHeight;
              const nav=document.querySelector('.bottomnav');
              const cta=document.querySelector('.sticky-cta');
              if (cta && nav){ cta.classList.remove('hidden');
                const c=cta.getBoundingClientRect(), n=nav.getBoundingClientRect();
                if (c.bottom>n.top+2 && c.top<n.bottom-2) out.push('кнопка объявления накрывает нижнюю панель: перекрытие '+Math.round(Math.min(c.bottom,n.bottom)-Math.max(c.top,n.top))+' точек');
                out.push('кнопка объявления: низ в '+Math.round(H-c.bottom)+' от края, нижнее поле '+getComputedStyle(cta).paddingBottom);
              }
              const inp=document.querySelector('.chat-input, .chat-compose, form.chat-send');
              if (inp){ const r=inp.getBoundingClientRect();
                out.push('поле переписки: низ в '+Math.round(H-r.bottom)+' от края, нижнее поле '+getComputedStyle(inp).paddingBottom+' (полоска '+sab+')'); }
              return out}""", [SAT, SAB])
            for e in extra: print("    ", e)
            top=[f for f in found]
            print(("✗ " if top else "✓ ")+rt)
            for f in found: print("    ",f)
            if top: bad+=1
            pg.evaluate(f"""()=>{{const mk=(t)=>{{const d=document.createElement('div');
              d.style.cssText='position:fixed;left:0;right:0;z-index:9999;background:rgba(255,0,0,.18);pointer-events:none;'+t;
              document.body.appendChild(d)}};
              mk('top:0;height:{SAT}px'); mk('bottom:0;height:{SAB}px')}}""")
            pg.screenshot(path=f"/tmp/shots/pwa-{(rt.strip('/').replace('/','_').split('?')[0] or 'home')[:28]}.png")
            pg.close()
        print("страниц с наездом:", bad)
        b.close()
finally:
    for x in pr: x.terminate()
    os.remove(f"{ROOT}/frontend/vite.pwa.mjs")
