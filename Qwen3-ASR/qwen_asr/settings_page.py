"""Standalone model-provider settings page for the streaming demo."""

SETTINGS_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Model Providers · Qwen3 Voice Agent</title>
  <style>
    :root{
      --bg:#090b0f; --surface:#11151b; --panel:#151a21; --input:#0d1117;
      --border:#2a323d; --border-strong:#46515f; --text:#f2f5f9; --muted:#9aa6b5;
      --green:#34d399; --green-bg:rgba(16,185,129,.13); --amber:#fbbf24;
      --red:#fb7185; --blue:#7dd3fc;
    }
    *{box-sizing:border-box}
    body{margin:0;background:var(--bg);color:var(--text);font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
    button,input,select{font:inherit;letter-spacing:0}
    button{cursor:pointer}
    .shell{min-height:100vh}
    .topbar{height:60px;border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 24px;gap:16px;background:var(--surface)}
    .back{color:var(--blue);text-decoration:none;font-size:14px;white-space:nowrap}
    .title{font-size:16px;font-weight:750}
    .subtitle{font-size:12px;color:var(--muted);margin-left:auto}
    .layout{display:grid;grid-template-columns:260px minmax(0,1fr);min-height:calc(100vh - 60px)}
    .sidebar{border-right:1px solid var(--border);padding:18px 14px;background:#0d1015}
    .sidebar-head{display:flex;align-items:center;justify-content:space-between;margin:0 4px 12px}
    .sidebar-head span{font-size:12px;color:var(--muted);text-transform:uppercase}
    .icon-button{width:30px;height:30px;border:1px solid var(--border);border-radius:6px;background:var(--panel);color:var(--text);font-size:20px;line-height:1}
    .icon-button:hover{border-color:var(--border-strong);background:#202731}
    .provider-list{display:flex;flex-direction:column;gap:6px}
    .provider-item{width:100%;min-height:54px;border:1px solid transparent;border-radius:6px;padding:9px 10px;background:transparent;color:var(--text);text-align:left;display:grid;grid-template-columns:1fr auto;gap:3px 8px;align-items:center}
    .provider-item:hover{background:var(--panel)}
    .provider-item.selected{background:#1a2028;border-color:var(--border-strong)}
    .provider-name{font-size:13px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .provider-model{font-size:11px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .dot{width:8px;height:8px;border-radius:50%;background:#4b5563;grid-row:1 / span 2;grid-column:2}
    .dot.ready{background:var(--green)} .dot.active{box-shadow:0 0 0 4px rgba(52,211,153,.12)}
    .content{padding:28px clamp(20px,4vw,56px);max-width:1120px;width:100%;margin:0 auto}
    .content-head{display:flex;align-items:flex-start;gap:16px;margin-bottom:24px}
    h1{font-size:22px;margin:0 0 6px;letter-spacing:0}.description{margin:0;color:var(--muted);font-size:13px}
    .active-badge{margin-left:auto;border:1px solid rgba(52,211,153,.45);background:var(--green-bg);color:#a7f3d0;border-radius:999px;padding:6px 10px;font-size:12px;white-space:nowrap}
    .form-section{border-top:1px solid var(--border);padding:20px 0}
    .section-title{font-size:13px;font-weight:750;margin:0 0 14px}.section-note{color:var(--muted);font-size:12px;font-weight:400;margin-left:8px}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
    .field{display:flex;flex-direction:column;gap:7px;min-width:0}.field.full{grid-column:1 / -1}
    label{font-size:12px;color:#c8d0da}
    input[type="text"],input[type="password"],input[type="number"],select{width:100%;height:40px;border:1px solid var(--border);border-radius:6px;padding:0 11px;background:var(--input);color:var(--text);outline:none}
    input:focus,select:focus{border-color:#6b7a8d;box-shadow:0 0 0 3px rgba(125,211,252,.08)}
    input:disabled{opacity:.65}.hint{font-size:11px;color:var(--muted);line-height:1.45}
    .secret-wrap{display:grid;grid-template-columns:1fr auto;gap:8px}.secret-toggle{width:50px;border:1px solid var(--border);border-radius:6px;background:var(--panel);color:var(--muted)}
    .range-row{display:grid;grid-template-columns:1fr 70px;gap:10px;align-items:center}input[type="range"]{accent-color:var(--green);width:100%}
    .check{display:flex;flex-direction:row;align-items:center;gap:8px;color:var(--muted);font-size:12px}.check input{accent-color:var(--green)}
    .actions{display:flex;gap:9px;align-items:center;flex-wrap:wrap;padding-top:20px;border-top:1px solid var(--border)}
    .btn{height:38px;border:1px solid var(--border);border-radius:6px;padding:0 14px;background:var(--panel);color:var(--text);font-weight:700;font-size:13px}
    .btn:hover{border-color:var(--border-strong);background:#202731}.btn.primary{background:var(--green-bg);border-color:rgba(52,211,153,.45);color:#c6fae6}.btn.danger{color:#fecdd3;border-color:rgba(251,113,133,.35)}
    .btn:disabled{opacity:.5;cursor:wait}.status{min-height:22px;margin-left:auto;font-size:12px;color:var(--muted)}.status.ok{color:var(--green)}.status.err{color:var(--red)}.status.wait{color:var(--amber)}
    .empty{padding:30px;color:var(--muted);text-align:center}
    @media(max-width:800px){.topbar{padding:0 16px}.subtitle{display:none}.layout{grid-template-columns:1fr}.sidebar{border-right:0;border-bottom:1px solid var(--border);padding:12px}.provider-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.content{padding:22px 16px}.content-head{flex-wrap:wrap}.active-badge{margin-left:0}.grid{grid-template-columns:1fr}.field.full{grid-column:auto}.status{width:100%;margin-left:0}}
    @media(max-width:460px){.topbar{gap:10px}.title{font-size:14px}.content-head h1{font-size:19px}.actions .btn{width:100%;flex:none}}
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <a class="back" href="/">Back / 返回</a>
      <div class="title">Qwen3 Voice Agent</div>
      <div class="subtitle">Model provider settings / 大模型厂商设置</div>
    </header>
    <main class="layout">
      <aside class="sidebar">
        <div class="sidebar-head"><span>Providers</span><button id="addProvider" class="icon-button" title="Add custom provider" aria-label="Add custom provider">+</button></div>
        <div id="providerList" class="provider-list"></div>
      </aside>
      <section class="content">
        <div id="empty" class="empty">Loading providers / 正在读取厂商</div>
        <form id="providerForm" hidden>
          <div class="content-head">
            <div><h1 id="formTitle"></h1><p class="description" id="formDescription"></p></div>
            <span id="activeBadge" class="active-badge" hidden>Active / 当前使用</span>
          </div>
          <section class="form-section">
            <h2 class="section-title">Provider / 厂商</h2>
            <div class="grid">
              <div class="field"><label for="providerName">Display name / 显示名称</label><input id="providerName" type="text" required /></div>
              <div class="field"><label for="providerId">Provider ID</label><input id="providerId" type="text" required pattern="[a-z0-9][a-z0-9_-]{0,63}" /></div>
              <div class="field"><label for="protocol">API protocol / API 协议</label><select id="protocol"><option value="openai">OpenAI Compatible</option><option value="anthropic">Anthropic Messages</option><option value="google_genai">Google Generative AI</option></select></div>
              <div class="field"><label for="baseUrl">Base URL</label><input id="baseUrl" type="text" placeholder="Provider default" /><span class="hint">OpenAI-compatible custom providers require a full API base URL.</span></div>
            </div>
          </section>
          <section class="form-section">
            <h2 class="section-title">Model & credentials / 模型与凭据 <span class="section-note">密钥只保存在服务器</span></h2>
            <div class="grid">
              <div class="field full"><label for="modelId">Model ID</label><input id="modelId" type="text" list="modelOptions" required /><datalist id="modelOptions"></datalist></div>
              <div class="field full"><label for="apiKey">API key</label><div class="secret-wrap"><input id="apiKey" type="password" autocomplete="new-password" /><button id="toggleSecret" class="secret-toggle" type="button" title="Show or hide API key">View</button></div><span id="keyHint" class="hint"></span></div>
              <label id="clearKeyRow" class="check field full" hidden><input id="clearKey" type="checkbox" /> Remove saved API key / 清除已保存密钥</label>
              <label class="check field full"><input id="requiresKey" type="checkbox" checked /> This provider requires an API key / 需要 API Key</label>
            </div>
          </section>
          <section class="form-section">
            <h2 class="section-title">Generation / 生成参数</h2>
            <div class="grid">
              <div class="field"><label for="temperature">Temperature</label><div class="range-row"><input id="temperature" type="range" min="0" max="2" step="0.1" /><input id="temperatureValue" type="number" min="0" max="2" step="0.1" /></div></div>
              <div class="field"><label for="maxTokens">Maximum output tokens</label><input id="maxTokens" type="number" min="1" max="65536" /></div>
            </div>
          </section>
          <div class="actions">
            <button id="saveActive" class="btn primary" type="submit">Save & activate / 保存并启用</button>
            <button id="saveOnly" class="btn" type="button">Save / 保存</button>
            <button id="testConnection" class="btn" type="button">Test / 测试连接</button>
            <button id="deleteProvider" class="btn danger" type="button" hidden>Delete / 删除</button>
            <span id="status" class="status" aria-live="polite"></span>
          </div>
        </form>
      </section>
    </main>
  </div>
<script>
(() => {
  const $ = id => document.getElementById(id);
  const els = {list:$("providerList"),form:$("providerForm"),empty:$("empty"),title:$("formTitle"),description:$("formDescription"),active:$("activeBadge"),name:$("providerName"),id:$("providerId"),protocol:$("protocol"),baseUrl:$("baseUrl"),model:$("modelId"),modelOptions:$("modelOptions"),apiKey:$("apiKey"),keyHint:$("keyHint"),clearKey:$("clearKey"),clearKeyRow:$("clearKeyRow"),requiresKey:$("requiresKey"),temperature:$("temperature"),temperatureValue:$("temperatureValue"),maxTokens:$("maxTokens"),status:$("status"),saveActive:$("saveActive"),saveOnly:$("saveOnly"),test:$("testConnection"),remove:$("deleteProvider")};
  let settings = {providers:[],active_provider:""};
  let selectedId = "";
  let creating = false;

  function selected(){ return settings.providers.find(item => item.id === selectedId); }
  function setStatus(message, kind=""){ els.status.textContent=message; els.status.className="status "+kind; }
  function setBusy(on){ [els.saveActive,els.saveOnly,els.test,els.remove].forEach(button => button.disabled=on); }
  function renderList(){
    els.list.innerHTML="";
    settings.providers.forEach(provider => {
      const button=document.createElement("button"); button.type="button"; button.className="provider-item"+(provider.id===selectedId?" selected":"");
      const name=document.createElement("span"); name.className="provider-name"; name.textContent=provider.name;
      const model=document.createElement("span"); model.className="provider-model"; model.textContent=provider.model || "No model";
      const dot=document.createElement("span"); dot.className="dot"+(provider.configured?" ready":"")+(provider.id===settings.active_provider?" active":"");
      button.append(name,model,dot); button.onclick=()=>{selectedId=provider.id;creating=false;render();}; els.list.appendChild(button);
    });
  }
  function renderForm(){
    const provider=selected();
    if(!provider){els.form.hidden=true;els.empty.hidden=false;return;}
    els.form.hidden=false;els.empty.hidden=true;els.title.textContent=provider.name;els.description.textContent=(provider.protocol==="openai"?"OpenAI-compatible API":provider.protocol==="anthropic"?"Anthropic Messages API":"Google Generative AI")+" · "+(provider.model||"No model selected");
    els.active.hidden=provider.id!==settings.active_provider;els.name.value=provider.name||"";els.id.value=provider.id||"";els.id.disabled=Boolean(provider.built_in)&&!creating;els.protocol.value=provider.protocol||"openai";els.baseUrl.value=provider.base_url||"";els.model.value=provider.model||"";
    els.modelOptions.innerHTML="";(provider.models||[]).forEach(value=>{const option=document.createElement("option");option.value=value;els.modelOptions.appendChild(option)});
    els.apiKey.value="";els.apiKey.placeholder=provider.has_api_key?"Saved / 已保存":"Enter API key";els.keyHint.textContent=provider.has_api_key?"A key is saved. Leave blank to keep it unchanged. / 已保存密钥，留空则不修改。":"No key saved / 尚未保存密钥";els.clearKey.checked=false;els.clearKeyRow.hidden=!provider.has_api_key;
    els.requiresKey.checked=provider.requires_key!==false;els.temperature.value=provider.temperature??0.2;els.temperatureValue.value=provider.temperature??0.2;els.maxTokens.value=provider.max_tokens??256;els.remove.hidden=Boolean(provider.built_in)||creating;setStatus("");
  }
  function render(){renderList();renderForm()}
  async function api(url, options={}){const response=await fetch(url,{headers:{"Content-Type":"application/json"},...options});const body=await response.json().catch(()=>({error:response.statusText}));if(!response.ok)throw new Error(body.error||response.statusText);return body}
  function payload(active){return {id:els.id.value.trim().toLowerCase(),name:els.name.value.trim(),protocol:els.protocol.value,base_url:els.baseUrl.value.trim(),model:els.model.value.trim(),api_key:els.apiKey.value,clear_api_key:els.clearKey.checked,requires_key:els.requiresKey.checked,temperature:Number(els.temperatureValue.value),max_tokens:Number(els.maxTokens.value),active}}
  async function load(){settings=await api("/api/settings");selectedId=settings.active_provider||settings.providers[0]?.id||"";render()}
  async function save(active){setBusy(true);setStatus("Saving / 正在保存","wait");try{settings=await api("/api/settings/provider",{method:"PUT",body:JSON.stringify(payload(active))});selectedId=els.id.value.trim().toLowerCase();creating=false;render();setStatus(active?"Saved and activated / 已保存并启用":"Saved / 已保存","ok")}catch(err){setStatus(err.message,"err")}finally{setBusy(false)}}
  els.form.onsubmit=event=>{event.preventDefault();save(true)};els.saveOnly.onclick=()=>save(false);
  els.test.onclick=async()=>{setBusy(true);setStatus("Testing connection / 正在测试连接","wait");try{const result=await api("/api/settings/test",{method:"POST",body:JSON.stringify(payload(false))});setStatus("Connected in "+result.latency_ms+" ms / 连接成功","ok")}catch(err){setStatus(err.message,"err")}finally{setBusy(false)}};
  els.remove.onclick=async()=>{if(!confirm("Delete this custom provider? / 删除该自定义厂商？"))return;setBusy(true);try{settings=await api("/api/settings/provider/"+encodeURIComponent(selectedId),{method:"DELETE"});selectedId=settings.active_provider;creating=false;render()}catch(err){setStatus(err.message,"err")}finally{setBusy(false)}};
  $("addProvider").onclick=()=>{const id="custom-"+Date.now().toString(36);settings.providers.push({id,name:"Custom provider",protocol:"openai",base_url:"http://127.0.0.1:8000/v1",model:"",models:[],requires_key:true,built_in:false,has_api_key:false,temperature:0.2,max_tokens:256});selectedId=id;creating=true;render()};
  $("toggleSecret").onclick=()=>{els.apiKey.type=els.apiKey.type==="password"?"text":"password"};els.temperature.oninput=()=>{els.temperatureValue.value=els.temperature.value};els.temperatureValue.oninput=()=>{els.temperature.value=els.temperatureValue.value};
  load().catch(err=>{els.empty.textContent="Cannot load settings / 无法加载设置: "+err.message});
})();
</script>
</body>
</html>"""
