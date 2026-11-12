(function () {
  "use strict";
  const cfg = window.AUDITA_CONSULTAS_CONFIG || {};
  const $ = id => document.getElementById(id);
  const form = $("cqForm"), log = $("cqLog"), input = $("cqInput"), send = $("cqSend");
  if (!form || !log || !input || !send) return;
  let remaining = Math.max(0, Number(cfg.restantes) || 0);
  let completed = Number(cfg.realizadas) || 0;
  let busy = false;
  let history = [];
  const MAX = 5;
  const mods = [
    {re:/planea|materialidad|riesgo de auditor|estrategia/i, view:"plan", label:"Abrir Planeación"},
    {re:/control interno|coso|segregaci|cuestionario/i, view:"ci", label:"Abrir Control Interno"},
    {re:/procedimiento|programa|muestr|confirmaci|inventario/i, view:"proc", label:"Abrir Procedimientos"},
    {re:/cierre|dictamen|opini[oó]n|salvedad|informe final/i, view:"cierre", label:"Abrir Cierre"}
  ];
  function updateQuota() {
    const used = Math.max(0, MAX - remaining);
    $("quotaPill").innerHTML = "Cupo por recarga · <b>" + remaining + " de 5</b> disponibles";
    $("cqLeft").textContent = remaining ? remaining + " consultas disponibles por recarga" : "Sin cupo; solicita recarga al administrador";
    $("cqDots").innerHTML = Array.from({length:MAX}, (_,i)=>'<i class="'+(i<used?'used':'')+'"></i>').join("");
    send.disabled = busy || remaining === 0;
    input.disabled = remaining === 0;
  }
  function bubble(kind, content) {
    $("cqEmpty")?.remove();
    const el=document.createElement("div"); el.className=kind==="user"?"msg-user":"msg-ai";
    const text=document.createElement("div"); text.textContent=content; el.appendChild(text);
    log.appendChild(el);log.scrollTop=log.scrollHeight;
    return {el,text};
  }
  function updateHistory() {
    const root=$("cqHist");root.replaceChildren();
    if (!history.length) {root.textContent="Aún no hay consultas en esta pantalla.";return;}
    history.slice(0,6).forEach(item=>{
      const el=document.createElement("button");el.type="button";el.className="hist-item";
      el.style.cssText="display:block;width:100%;text-align:left;background:white;border:1px solid #e5e7eb;border-radius:6px;margin:4px 0;padding:8px;cursor:pointer";
      const strong=document.createElement("strong");strong.textContent=item.q;
      const para=document.createElement("div");para.textContent=item.a.slice(0,95);
      el.append(strong,para);el.onclick=()=>{log.replaceChildren();bubble("user",item.q);bubble("ai",item.a)};
      root.appendChild(el);
    });
  }
  async function ask(raw) {
    const question=String(raw||"").trim();
    if (!question || busy || remaining===0) return;
    if (question.length>1800) {alert("La consulta debe tener hasta 1800 caracteres.");return;}
    busy=true;updateQuota();$("cqSugs").hidden=true;
    bubble("user",question);
    const {el,text}=bubble("ai","Consultando el servicio…");
    $("cqStatus").textContent="Respondiendo…";
    const body=new FormData();body.append("pregunta",question);
    try {
      const response=await fetch(cfg.endpoint,{method:"POST",body,credentials:"same-origin",headers:{"X-CSRFToken":cfg.token}});
      const data=await response.json();
      if(typeof data.restantes==="number")remaining=data.restantes;
      if(typeof data.realizadas==="number")completed=data.realizadas;
      if(!response.ok || data.error)throw new Error(data.error||"No fue posible completar la consulta.");
      text.textContent=data.respuesta||"El servicio no devolvió una respuesta.";
      history.unshift({q:question,a:text.textContent});history=history.slice(0,20);updateHistory();
      const related=mods.find(m=>m.re.test(question));
      if(related && typeof window.switchTab==="function") {
        const button=document.createElement("button");button.type="button";button.className="cq-goto";button.textContent=related.label+" →";
        button.onclick=()=>window.switchTab(related.view);el.appendChild(button);
      }
    } catch(err) {text.textContent=err.message||"Error temporal. Intenta de nuevo.";}
    finally {busy=false;updateQuota();$("cqStatus").textContent="Listo para responder";log.scrollTop=log.scrollHeight;}
  }
  form.addEventListener("submit",e=>{e.preventDefault();const q=input.value;input.value="";ask(q)});
  input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();form.requestSubmit()}});
  document.querySelectorAll(".cq-sug").forEach(button=>button.addEventListener("click",()=>ask(button.textContent)));
  $("cqClear").addEventListener("click",()=>{log.replaceChildren();history=[];updateHistory();$("cqSugs").hidden=false;});
  updateHistory();updateQuota();
})();
