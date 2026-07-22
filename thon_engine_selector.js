(function(){
  if (window.__THON_ENGINE_SELECTOR_SAFE__) return;
  window.__THON_ENGINE_SELECTOR_SAFE__ = true;

  const css = `
  .thon-engine-select-safe{box-sizing:border-box;display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:12px 0;padding:12px 14px;border:1px solid rgba(53,242,143,.20);background:rgba(6,18,14,.72);border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.18);font-family:inherit;color:inherit;}
  .thon-engine-select-safe .tes-left{display:flex;flex-direction:column;gap:3px;min-width:220px;}
  .thon-engine-select-safe .tes-title{font-weight:800;letter-spacing:.02em;color:#35f28f;font-size:13px;text-transform:uppercase;}
  .thon-engine-select-safe .tes-desc{font-size:12px;opacity:.75;line-height:1.35;}
  .thon-engine-select-safe select{appearance:auto;min-width:240px;padding:10px 12px;border-radius:10px;border:1px solid rgba(53,242,143,.28);background:#070b0f;color:#f4fff8;font:inherit;font-size:13px;outline:none;}
  .thon-engine-select-safe .tes-status{font-size:12px;opacity:.72;min-width:120px;text-align:right;}
  @media(max-width:760px){.thon-engine-select-safe{align-items:stretch}.thon-engine-select-safe select{width:100%;min-width:0}.thon-engine-select-safe .tes-status{text-align:left}}
  `;

  function ready(fn){ if(document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn); }
  function norm(v){ v = String(v||'api').toLowerCase(); if(v.includes('multi_source') || v.includes('multisource')) return 'api_multi_source_fast'; return v.includes('dlp') || v.includes('ytdlp') || v.includes('yt-dlp') ? 'dlp' : 'api'; }
  function currentMode(){ return norm(localStorage.getItem('thon_engine_mode') || 'api'); }
  function modeLabel(m){ return m === 'dlp' ? 'DLP completo: busca + verifica + Auto Hunt' : (m === 'api_multi_source_fast' ? 'API multi-source: vídeo + canal + playlist' : 'API: acha canais; DLP verifica automático'); }

  async function saveMode(mode){
    mode = norm(mode);
    localStorage.setItem('thon_engine_mode', mode);
    try{
      const r = await fetch('/api/engine_mode', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode})});
      return await r.json();
    }catch(e){ return {ok:false, erro:String(e)}; }
  }

  function patchFetch(){
    if (window.__THON_ENGINE_FETCH_PATCH__) return;
    window.__THON_ENGINE_FETCH_PATCH__ = true;
    const original = window.fetch;
    window.fetch = function(input, init){
      try{
        const url = (typeof input === 'string') ? input : (input && input.url) || '';
        if ((url.includes('/iniciar') || url.includes('/auto_hunt')) && init && init.method && String(init.method).toUpperCase() === 'POST'){
          const mode = currentMode();
          const headers = Object.assign({}, init.headers || {}, {'Content-Type':'application/json'});
          let body = {};
          if (init.body) {
            try { body = JSON.parse(init.body); } catch(e) { body = {}; }
          }
          body.engine_mode = mode;
          body.modo_coleta = mode;
          body.collect_mode = mode;
          // Auto Hunt só faz sentido no DLP. No modo API, o backend também bloqueia.
          if (url.includes('/auto_hunt') && body.enabled === true && mode !== 'dlp'){
            alert('Auto Hunt fica só no DLP. No modo API, clique em iniciar: a API acha canais e o DLP verifica automático até acabar.');
            return Promise.resolve(new Response(JSON.stringify({ok:false, erro:'Auto Hunt só no DLP', enabled:false}), {status:400, headers:{'Content-Type':'application/json'}}));
          }
          init = Object.assign({}, init, {headers, body: JSON.stringify(body)});
        }
      }catch(e){}
      return original.call(this, input, init);
    };
  }

  function findMount(){
    const candidates = [
      '[data-prospector-controls]', '.prospector-controls', '.controls', '.toolbar', '.filter-bar', '.actions',
      'form', 'main .card', '.card', 'main', '#app', '.container', 'body'
    ];
    for (const sel of candidates){
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return document.body;
  }

  ready(async function(){
    patchFetch();
    const path = location.pathname.toLowerCase();
    if (!path.includes('prospector') && !path.includes('crm')) return;
    if (!document.getElementById('thon-engine-style')){
      const st = document.createElement('style'); st.id='thon-engine-style'; st.textContent=css; document.head.appendChild(st);
    }
    if (document.getElementById('thon-engine-select-safe')) return;

    const box = document.createElement('div');
    box.className = 'thon-engine-select-safe';
    box.id = 'thon-engine-select-safe';
    box.innerHTML = `
      <div class="tes-left">
        <div class="tes-title">Engine do Prospector</div>
        <div class="tes-desc">Escolha como esta busca vai rodar. API acha volume rápido; DLP faz a verificação pesada.</div>
      </div>
      <select id="thonEngineSelectSafe" aria-label="Engine do Prospector">
        <option value="api">API → achar canais + DLP verifica automático</option>
        <option value="api_multi_source_fast">API Multi-source rápida → vídeo + canal + playlist</option>
        <option value="dlp">DLP completo → buscar + verificar + Auto Hunt</option>
      </select>
      <div class="tes-status" id="thonEngineStatusSafe"></div>`;

    const mount = findMount();
    if (mount === document.body) document.body.insertBefore(box, document.body.firstChild);
    else mount.insertBefore(box, mount.firstChild);

    const select = box.querySelector('#thonEngineSelectSafe');
    const status = box.querySelector('#thonEngineStatusSafe');
    let mode = currentMode();
    try{
      const j = await fetch('/api/engine_mode').then(r=>r.json());
      if (j && j.mode) mode = norm(j.mode);
    }catch(e){}
    select.value = mode;
    localStorage.setItem('thon_engine_mode', mode);
    status.textContent = modeLabel(mode);

    select.addEventListener('change', async function(){
      const m = norm(select.value);
      status.textContent = 'salvando engine...';
      const j = await saveMode(m);
      status.textContent = j && j.ok ? modeLabel(m) : 'erro ao salvar';
    });
  });
})();
