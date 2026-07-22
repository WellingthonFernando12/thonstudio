(function(){
  if (window.__THON_FULL_NAV_LOADED__) return;
  window.__THON_FULL_NAV_LOADED__ = true;

  const links = [
    ['/', 'Toolkit'],
    ['/dashboard', 'Dashboard'],
    ['/prospector', 'Prospector'],
    ['/crm', 'CRM'],
    ['/trabalhos', 'Trabalhos'],
    ['/projetos', 'Projetos'],
    ['/metas', 'Metas'],
    ['/downloader', 'Downloader'],
    ['/pipeline', 'Pipeline'],
    ['/api-keys', 'API Keys']
  ];

  const css = `
    :root{--thon-nav-h:46px;}
    body{padding-top:var(--thon-nav-h)!important;}
    #thon-full-nav{position:fixed;top:0;left:0;right:0;height:46px;z-index:2147483000;background:rgba(9,12,16,.96);border-bottom:1px solid rgba(255,255,255,.12);display:flex;align-items:center;gap:10px;padding:0 12px;font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Arial,sans-serif;box-sizing:border-box;backdrop-filter:blur(10px);}
    #thon-full-nav .thon-brand{font-weight:800;font-size:13px;letter-spacing:.04em;color:#fff;white-space:nowrap;margin-right:4px;}
    #thon-full-nav .thon-dot{width:8px;height:8px;border-radius:999px;background:#34d399;box-shadow:0 0 12px rgba(52,211,153,.7);}
    #thon-full-nav .thon-links{display:flex;gap:6px;overflow-x:auto;align-items:center;white-space:nowrap;padding-bottom:1px;}
    #thon-full-nav .thon-links::-webkit-scrollbar{height:0px;}
    #thon-full-nav a{color:rgba(255,255,255,.78);text-decoration:none;font-size:12px;font-weight:650;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.045);padding:7px 9px;border-radius:10px;line-height:1;}
    #thon-full-nav a:hover{color:#fff;background:rgba(255,255,255,.12);border-color:rgba(255,255,255,.22);}
    #thon-full-nav a.active{color:#07110d;background:#34d399;border-color:#34d399;}
    #thon-full-nav .thon-actions{margin-left:auto;display:flex;gap:6px;align-items:center;}
    #thon-full-nav button{cursor:pointer;color:rgba(255,255,255,.86);background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:7px 9px;font-size:12px;font-weight:700;line-height:1;}
    #thon-full-nav button:hover{background:rgba(255,255,255,.15);color:#fff;}
    @media(max-width:760px){#thon-full-nav{height:auto;min-height:46px;flex-wrap:wrap;padding:8px 10px;}body{padding-top:86px!important;}#thon-full-nav .thon-actions{display:none;}}
  `;

  const style = document.createElement('style');
  style.id = 'thon-full-nav-style';
  style.textContent = css;
  document.head.appendChild(style);

  const nav = document.createElement('div');
  nav.id = 'thon-full-nav';

  const brand = document.createElement('div');
  brand.className = 'thon-brand';
  brand.textContent = 'THON TOOLKIT';
  nav.appendChild(brand);

  const dot = document.createElement('span');
  dot.className = 'thon-dot';
  nav.appendChild(dot);

  const wrap = document.createElement('div');
  wrap.className = 'thon-links';
  const current = (location.pathname || '/').replace(/\/$/, '') || '/';
  for (const [href, label] of links){
    const a = document.createElement('a');
    a.href = href;
    a.textContent = label;
    const normalized = href.replace(/\/$/, '') || '/';
    if (current === normalized) a.className = 'active';
    wrap.appendChild(a);
  }
  nav.appendChild(wrap);

  const actions = document.createElement('div');
  actions.className = 'thon-actions';
  const status = document.createElement('button');
  status.textContent = 'Status';
  status.onclick = () => window.open('/estado', '_blank');
  const refresh = document.createElement('button');
  refresh.textContent = 'Atualizar';
  refresh.onclick = () => location.reload();
  actions.appendChild(status);
  actions.appendChild(refresh);
  nav.appendChild(actions);

  document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('thon-full-nav')) document.body.prepend(nav);
  });
})();
