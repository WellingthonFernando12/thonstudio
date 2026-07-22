
(function(){
  if (window.__thonV5818IndexLinks) return;
  window.__thonV5818IndexLinks = true;
  function add(){
    try{
      var links = [
        ['⚙️ API Keys','/api-keys'],
        ['🧠 Engine Console','/engine-console'],
        ['📦 Fila JSON','/api/v58_18/fila'],
        ['🩺 API State','/api/v58_18/api_state']
      ];
      var bar = document.createElement('div');
      bar.id='thon-v58-18-quickbar';
      bar.style.cssText='position:fixed;right:14px;bottom:14px;z-index:999999;background:#071312;border:1px solid rgba(0,255,170,.28);border-radius:14px;padding:10px;display:flex;gap:8px;flex-wrap:wrap;max-width:520px;box-shadow:0 12px 40px rgba(0,0,0,.45);font-family:system-ui,-apple-system,Segoe UI,sans-serif';
      links.forEach(function(x){
        var a=document.createElement('a');
        a.textContent=x[0]; a.href=x[1];
        a.style.cssText='color:#bfffe8;text-decoration:none;background:rgba(0,255,170,.08);border:1px solid rgba(0,255,170,.18);padding:7px 10px;border-radius:10px;font-size:12px;font-weight:700';
        bar.appendChild(a);
      });
      if(!document.getElementById('thon-v58-18-quickbar')) document.body.appendChild(bar);
    }catch(e){}
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', add); else add();
})();
