/* Archivo Permanente manual de AuditaPro.
 * Sin AJAX, sin peticiones a Django para guardar y sin dependencias externas.
 * ZIP OOXML nativo para Word. PDF a través de impresión del navegador.
 */
(function () {
  'use strict';
  const root = document.getElementById('apmRoot');
  if (!root || !window.AP_PERMANENT_SEED) return;
  const userId = String(root.dataset.userId || 'anonymous');
  const storageKey = 'auditapro:archivo-permanente:manual:v2:user:' + userId;
  const seed = window.AP_PERMANENT_SEED;
  const copy = value => JSON.parse(JSON.stringify(value));
  const nav = document.getElementById('apmNav');
  const panel = document.getElementById('apmPanel');
  const saveStatus = document.getElementById('apmSaveStatus');
  const company = document.getElementById('apmCompany');
  const period = document.getElementById('apmPeriod');
  const toastBox = document.getElementById('apmToast');
  let state = copy(seed), currentSection = '1', dirty = false, toastHandle = null;
  let idSequence = 0;

  function escapeHtml(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function escapeXml(v) { return escapeHtml(v); }
  function toast(message, error) {
    toastBox.textContent = message;
    toastBox.classList.toggle('error', !!error);
    toastBox.classList.add('show');
    clearTimeout(toastHandle);
    toastHandle = setTimeout(() => toastBox.classList.remove('show'), 3700);
  }
  function findTable(sectionId, tableId) {
    const section = state.sections.find(s => s.id === sectionId);
    return section && section.tables.find(t => t.id === tableId);
  }
  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey));
      if (saved && saved.version === 2 && saved.payload && Array.isArray(saved.payload.sections) && saved.payload.sections.length === 6) {
        state = saved.payload;
      }
    } catch (e) { console.warn('Archivo Permanente: datos guardados no legibles.', e); }
  }
  function markDirty() {
    dirty = true;
    saveStatus.textContent = 'Cambios sin guardar';
    saveStatus.classList.add('is-dirty');
  }
  function save() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({version:2, payload:state, savedAt:new Date().toISOString()}));
      dirty = false;
      const time = new Date().toLocaleTimeString('es-CO', {hour:'2-digit',minute:'2-digit'});
      saveStatus.textContent = 'Guardado a las ' + time;
      saveStatus.classList.remove('is-dirty');
      toast('Cambios guardados en este navegador.');
      return true;
    } catch (e) {
      toast('No se pudo guardar: revisa el almacenamiento del navegador.', true);
      return false;
    }
  }
  function renderNav() {
    nav.innerHTML = state.sections.map(s => `<button type="button" class="apm-navbtn ${s.id===currentSection?'active':''}" data-section="${escapeHtml(s.id)}" aria-current="${s.id===currentSection?'page':'false'}"><span class="apm-num">${escapeHtml(s.id)}</span><span>${escapeHtml(s.title)}</span></button>`).join('');
  }
  function parseAmount(v) {
    let s = String(v == null ? '' : v).replace(/[^0-9,.-]/g,'').trim();
    if (!s) return NaN;
    const comma = s.lastIndexOf(','), dot = s.lastIndexOf('.');
    if (comma !== -1 && dot !== -1) {
      // "1,234.50" o "1.234,50".
      s = comma > dot ? s.replace(/\./g,'').replace(/,/g,'.') : s.replace(/,/g,'');
    } else if (comma !== -1) {
      // Varias comas de agrupación, o coma decimal en valores locales.
      s = /^-?\d{1,3}(,\d{3})+$/.test(s) ? s.replace(/,/g,'') : s.replace(',','.');
    } else if (dot !== -1 && /^-?\d{1,3}(\.\d{3})+$/.test(s)) {
      s = s.replace(/\./g,'');
    }
    const result = Number(s);
    return Number.isFinite(result) ? result : NaN;
  }
  function variation(row) {
    const real = parseAmount(row.cells[1]);
    const budget = parseAmount(row.cells[2]);
    if (!Number.isFinite(real) || !Number.isFinite(budget) || budget === 0) return '—';
    const percentage = (real - budget) / budget * 100;
    return (percentage > 0 ? '+' : '') + percentage.toFixed(1) + '%';
  }
  function cellText(table,row,index) {
    return index === table.calcIndex ? variation(row) : String(row.cells[index] ?? '');
  }
  function renderPanel() {
    const section = state.sections.find(s => s.id===currentSection);
    if (!section) return;
    panel.innerHTML = `
      <header class="apm-section-head"><div><div class="apm-overline">SECCIÓN ${escapeHtml(section.id)} DE 6</div><h2>${escapeHtml(section.title)}</h2><p>${escapeHtml(state.meta.company || 'Entidad sin nombre')} · ${escapeHtml(state.meta.period || 'Período por diligenciar')}</p></div>
      <div class="apm-section-actions"><button type="button" class="apm-btn apm-btn-word" data-export="word" data-scope="current"><i class="bi bi-file-earmark-word"></i> Word</button><button type="button" class="apm-btn apm-btn-pdf" data-export="pdf" data-scope="current"><i class="bi bi-file-earmark-pdf"></i> PDF</button></div></header>
      <div class="apm-callout"><i class="bi bi-pencil-square"></i> Los campos se editan directamente. Las variaciones porcentuales de resultados se calculan con los datos introducidos; no se consultan otras áreas del sistema.</div>
      ${section.tables.map(table => `
        <article class="apm-table-card" data-table-card="${escapeHtml(table.id)}">
          <div class="apm-table-top"><div><h3>${escapeHtml(table.title)}</h3><p>${escapeHtml(table.description)}</p></div></div>
          <div class="apm-table-wrap"><table class="apm-table"><thead><tr>${table.columns.map(col => `<th scope="col">${escapeHtml(col)}</th>`).join('')}<th scope="col">Acciones</th></tr></thead>
          <tbody>${table.rows.map(row => `<tr data-row-id="${escapeHtml(row.id)}">${table.columns.map((col,index) => {
            if (index === table.calcIndex) {
              const v = variation(row);
              return `<td><span class="apm-cell-calculated ${v.startsWith('-')?'negative':''}" data-variation>${escapeHtml(v)}</span></td>`;
            }
            const guide = (row.guides || [])[index] || '';
            return `<td><input type="text" class="apm-cell-input" data-index="${index}" value="${escapeHtml(row.cells[index] || '')}" aria-label="${escapeHtml(col)}" maxlength="1500" title="${escapeHtml(guide || col)}">${guide?`<small class="apm-guide">${escapeHtml(guide)}</small>`:''}</td>`;
          }).join('')}<td class="apm-table-action"><button type="button" class="apm-iconbtn" data-row-save title="Guardar fila" aria-label="Guardar fila"><i class="bi bi-floppy"></i></button><button type="button" class="apm-iconbtn danger" data-row-delete title="Eliminar fila" aria-label="Eliminar fila"><i class="bi bi-trash"></i></button></td></tr>`).join('')}</tbody></table></div>
          <footer class="apm-table-bottom"><button type="button" class="apm-btn apm-btn-primary" data-add="${escapeHtml(table.id)}"><i class="bi bi-plus-lg"></i> Añadir registro</button><span class="apm-table-meta">${table.rows.length} registros</span></footer>
        </article>`).join('')}`;
  }
  function updateMetadata() {
    state.meta.company = company.value;
    state.meta.period = period.value;
    markDirty();
    const subtitle = panel.querySelector('.apm-section-head p');
    if (subtitle) subtitle.textContent = (company.value || 'Entidad sin nombre') + ' · ' + (period.value || 'Período por diligenciar');
  }
  function rowContext(el) {
    const card = el.closest('[data-table-card]');
    const rowElement = el.closest('tr[data-row-id]');
    if (!card || !rowElement) return null;
    const table = findTable(currentSection, card.dataset.tableCard);
    if (!table) return null;
    const row = table.rows.find(r=>r.id===rowElement.dataset.rowId);
    return row ? {table,row,rowElement} : null;
  }
  function onInput(event) {
    const input = event.target.closest('input.apm-cell-input');
    if (!input) return;
    const ctx = rowContext(input);
    if (!ctx) return;
    ctx.row.cells[Number(input.dataset.index)] = input.value;
    if (ctx.table.calcIndex >= 0) {
      const badge = ctx.rowElement.querySelector('[data-variation]');
      if (badge) { const value=variation(ctx.row);badge.textContent=value;badge.classList.toggle('negative',value.startsWith('-')); }
    }
    markDirty();
  }
  function deleteRow(el) {
    const ctx = rowContext(el);
    if (!ctx) return;
    if (!confirm('¿Eliminar este registro del expediente manual?')) return;
    ctx.table.rows = ctx.table.rows.filter(r=>r.id!==ctx.row.id);
    renderPanel();
    markDirty();
    save();
  }
  function addRow(tableId) {
    const table=findTable(currentSection,tableId);
    if (!table) return;
    idSequence += 1;
    table.rows.push({id:'new-'+Date.now()+'-'+idSequence,cells:table.columns.map(()=>''), guides:table.columns.map(()=>'')});
    renderPanel();
    markDirty();
    const card = Array.from(panel.querySelectorAll('[data-table-card]')).find(c=>c.dataset.tableCard===tableId);
    if (card) {const rows=card.querySelectorAll('tbody tr');const input=rows[rows.length-1] && rows[rows.length-1].querySelector('input');if(input)input.focus();}
    toast('Registro añadido. Guarda los cambios para conservarlo.');
  }
  function safeFilename(s) { return String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zA-Z0-9_-]+/g,'_').slice(0,65); }
  function exportSections(scope) { return scope==='all'?state.sections:[state.sections.find(s=>s.id===currentSection)]; }

  /* Generador OOXML básico válido para Word (.docx). No requiere JSZip ni conexión externa. */
  function xmlText(text) {return `<w:r><w:t xml:space="preserve">${escapeXml(text)}</w:t></w:r>`;}
  function wordParagraph(text, fontSize, bold, after) {
    return `<w:p><w:pPr><w:spacing w:after="${after==null?130:after}"/></w:pPr><w:r><w:rPr>${bold?'<w:b/>':''}<w:sz w:val="${fontSize||20}"/></w:rPr><w:t xml:space="preserve">${escapeXml(text)}</w:t></w:r></w:p>`;
  }
  function wordCell(v, header, width) {
    return `<w:tc><w:tcPr><w:tcW w:w="${width}" w:type="dxa"/>${header?'<w:shd w:fill="E8F0FF"/>':''}</w:tcPr><w:p><w:r><w:rPr>${header?'<w:b/>':''}<w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">${escapeXml(v)}</w:t></w:r></w:p></w:tc>`;
  }
  function wordTable(table) {
    const rows=[table.columns,...table.rows.map(r=>table.columns.map((c,i)=>cellText(table,r,i)))];
    const cols=table.columns.length, width=Math.floor(10300/cols);
    const grid='<w:tblGrid>'+table.columns.map(()=>`<w:gridCol w:w="${width}"/>`).join('')+'</w:tblGrid>';
    return `<w:tbl><w:tblPr><w:tblW w:w="10300" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders><w:top w:val="single" w:sz="4" w:color="DCE4F0"/><w:left w:val="single" w:sz="4" w:color="DCE4F0"/><w:bottom w:val="single" w:sz="4" w:color="DCE4F0"/><w:right w:val="single" w:sz="4" w:color="DCE4F0"/><w:insideH w:val="single" w:sz="4" w:color="E9EEF7"/><w:insideV w:val="single" w:sz="4" w:color="E9EEF7"/></w:tblBorders></w:tblPr>${grid}${rows.map((row,index)=>`<w:tr>${row.map(x=>wordCell(x,index===0,width)).join('')}</w:tr>`).join('')}</w:tbl>`;
  }
  function crc32(data) {
    let crc=-1;
    for(let i=0;i<data.length;i++) {crc^=data[i];for(let n=0;n<8;n++)crc=crc>>>1^((crc&1)?0xEDB88320:0);}
    return (crc ^ -1)>>>0;
  }
  function zipUint8(files) {
    const enc=new TextEncoder();let offset=0;const local=[],central=[];
    function put16(b,p,v){b[p]=v&255;b[p+1]=(v>>>8)&255;}
    function put32(b,p,v){put16(b,p,v&65535);put16(b,p+2,(v>>>16)&65535);}
    for(const file of files){
      const name=enc.encode(file.name),data=enc.encode(file.content),crc=crc32(data);
      const l=new Uint8Array(30+name.length+data.length);
      put32(l,0,0x04034b50);put16(l,4,20);put16(l,6,0x0800);put16(l,8,0);put32(l,14,crc);put32(l,18,data.length);put32(l,22,data.length);put16(l,26,name.length);l.set(name,30);l.set(data,30+name.length);
      const c=new Uint8Array(46+name.length);put32(c,0,0x02014b50);put16(c,4,20);put16(c,6,20);put16(c,8,0x0800);put32(c,16,crc);put32(c,20,data.length);put32(c,24,data.length);put16(c,28,name.length);put32(c,42,offset);c.set(name,46);
      local.push(l);central.push(c);offset+=l.length;
    }
    const centralSize=central.reduce((a,c)=>a+c.length,0),total=offset+centralSize+22;
    const all=new Uint8Array(total);let p=0;
    for(const b of local){all.set(b,p);p+=b.length;}
    const centerStart=p;for(const b of central){all.set(b,p);p+=b.length;}
    put32(all,p,0x06054b50);put16(all,p+8,files.length);put16(all,p+10,files.length);put32(all,p+12,centralSize);put32(all,p+16,centerStart);
    return all;
  }
  function downloadBlob(blob,name){
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.style.display='none';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),6000);
  }
  function exportWord(scope) {
    const secs=exportSections(scope);let body=wordParagraph('ARCHIVO PERMANENTE',32,true,160)+wordParagraph(state.meta.company||'Entidad sin nombre',24,true,100)+wordParagraph('Período: '+(state.meta.period||'Sin especificar'),20,false,220);
    for(const s of secs){body+=wordParagraph(s.id+'. '+s.title,27,true,180);for(const t of s.tables){body+=wordParagraph(t.title,22,true,100)+wordTable(t)+wordParagraph('',16,false,160);}}
    body+='<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="900" w:right="700" w:bottom="900" w:left="700"/></w:sectPr>';
    const documentXml='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>';
    const files=[
      {name:'[Content_Types].xml',content:'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'},
      {name:'_rels/.rels',content:'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'},
      {name:'word/document.xml',content:documentXml}
    ];
    downloadBlob(new Blob([zipUint8(files)],{type:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}),'Archivo_Permanente_'+(scope==='all'?'Completo':'Seccion_'+currentSection)+'_'+safeFilename(state.meta.company||'Sin_nombre')+'.docx');
    toast('Documento Word .docx generado.');
  }

  /* Exportación PDF con motor nativo del navegador (Imprimir → Guardar como PDF).
   * Garantiza paginación y evita depender de CDNs o capturas que recortan tablas. */
  function exportPDF(scope) {
    const secs=exportSections(scope);
    const doc=window.open('','_blank');
    if(!doc){toast('Permite las ventanas emergentes para exportar el PDF.',true);return;}
    let content=`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Archivo Permanente</title><style>
      @page{size:A4;margin:15mm 12mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;font-size:11px;color:#17243b;margin:0}header{border-bottom:2px solid #2563eb;padding-bottom:10px;margin-bottom:18px}h1{font-size:20px;margin:0 0 6px}h2{font-size:16px;color:#1e40af;margin-top:22px}h3{font-size:12px}p{color:#586b85}table{border-collapse:collapse;width:100%;font-size:9px;table-layout:fixed;margin-bottom:20px}th,td{border:1px solid #d6deea;padding:6px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#edf4ff}tr{break-inside:avoid}section{break-inside:auto}section+section{break-before:page}button{font-size:12px;padding:8px 12px;cursor:pointer}@media print{.print-btn{display:none}}
    </style></head><body><div class="print-btn"><button onclick="window.print()">Imprimir / Guardar como PDF</button><span> Selecciona «Guardar como PDF» como destino.</span></div><header><h1>Archivo Permanente</h1><div>${escapeHtml(state.meta.company||'Entidad sin nombre')} · Período: ${escapeHtml(state.meta.period||'Sin especificar')}</div></header>`;
    for(const s of secs){content+=`<section><h2>${escapeHtml(s.id+'. '+s.title)}</h2>`;for(const t of s.tables){content+=`<h3>${escapeHtml(t.title)}</h3><table><thead><tr>${t.columns.map(c=>'<th>'+escapeHtml(c)+'</th>').join('')}</tr></thead><tbody>${t.rows.map(row=>'<tr>'+t.columns.map((col,index)=>'<td>'+escapeHtml(cellText(t,row,index))+'</td>').join('')+'</tr>').join('')}</tbody></table>`;}content+='</section>';}
    content+='</body></html>';
    doc.document.open();doc.document.write(content);doc.document.close();doc.focus();
    toast('Vista lista: selecciona «Guardar como PDF» en la ventana de impresión.');
  }

  // Inicialización y delegación de eventos
  load();company.value=state.meta.company||'';period.value=state.meta.period||'';renderNav();renderPanel();
  nav.addEventListener('click',e=>{const btn=e.target.closest('[data-section]');if(!btn)return;currentSection=btn.dataset.section;renderNav();renderPanel();});
  panel.addEventListener('input',onInput);
  panel.addEventListener('click',e=>{
    const add=e.target.closest('[data-add]');if(add){addRow(add.dataset.add);return;}
    const del=e.target.closest('[data-row-delete]');if(del){deleteRow(del);return;}
    const rowSave=e.target.closest('[data-row-save]');if(rowSave){save();return;}
  });
  root.addEventListener('click',e=>{const btn=e.target.closest('button[data-export]');if(!btn)return;if(btn.dataset.export==='word') exportWord(btn.dataset.scope);else exportPDF(btn.dataset.scope);});
  company.addEventListener('input',updateMetadata);period.addEventListener('input',updateMetadata);
  document.getElementById('apmSave').addEventListener('click',save);
  document.getElementById('apmRestore').addEventListener('click', () => {
    if (!confirm('¿Restaurar los ejemplos del mockup? Se reemplazarán los datos manuales guardados en este navegador para esta cuenta.')) return;
    state = copy(seed);
    company.value = state.meta.company;
    period.value = state.meta.period;
    currentSection = '1';
    renderNav();renderPanel();markDirty();save();
    toast('Ejemplos restaurados para esta cuenta.');
  });
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
})();
