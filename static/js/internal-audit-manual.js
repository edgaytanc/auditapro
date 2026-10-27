/* Auditoría Interna: panel estrictamente manual, aislado de Audit/cronograma.
   No realiza fetch, AJAX ni envía formularios al servidor. */
(function () {
  'use strict';
  const app = document.getElementById('iamApp');
  if (!app) return;
  const $ = id => document.getElementById(id);
  const userId = app.dataset.userId || 'anon';
  const STORAGE = `auditapro:interna-manual:v2:user:${userId}`;
  const STATUSES = {planificacion:'Planificación', proceso:'En proceso', seguimiento:'Seguimiento', finalizada:'Finalizada'};
  const RISKS = {alto:'Alto', medio:'Medio', bajo:'Bajo'};
  const TABS = [
    ['planificacion','Planificación'], ['riesgos','Matriz de Riesgos'],
    ['controles','Evaluación de Controles'], ['hallazgos','Hallazgos y Recomendaciones'],
    ['seguimiento','Seguimiento a Plan de Acción'], ['cronograma','Cronograma'],
    ['informe','Informe Final']
  ];
  const FIELDS = {
    riesgos: ['Proceso','Riesgo','Probabilidad','Impacto','Control','Conclusión'],
    controles: ['Control','Tipo','Diseño','Operación','Conclusión'],
    hallazgos: ['ID','Hallazgo','Proceso','Severidad','Recomendación','Responsable','Estado','Fecha'],
    seguimiento: ['Hallazgo','Acción','Estado','Avance (%)','Evidencia'],
    cronograma: ['Actividad','Responsable','Inicio','Fin','Estado','Avance (%)']
  };
  const SAMPLE_DATA = [
    {id:'AI-2025-011',proceso:'Compras y Pagos',cliente:'Distribuidora Pérez Hnos.',estado:'proceso',riesgo:'alto',auditor:'M. López',avance:65,cierre:'2026-08-02'},
    {id:'AI-2025-007',proceso:'Nómina',cliente:'Constructora Montaña S.A.',estado:'finalizada',riesgo:'medio',auditor:'C. Ruíz',avance:100,cierre:'2026-07-14'},
    {id:'AI-2025-014',proceso:'Tesorería',cliente:'Empresa ABC S.A.',estado:'seguimiento',riesgo:'medio',auditor:'R. García',avance:88,cierre:'2026-08-07'},
    {id:'AI-2025-018',proceso:'Inventarios',cliente:'Distribuidora Pérez Hnos.',estado:'planificacion',riesgo:'alto',auditor:'M. López',avance:15,cierre:'2026-08-29'},
    {id:'AI-2025-020',proceso:'Tecnología de la Información',cliente:'Empresa ABC S.A.',estado:'proceso',riesgo:'bajo',auditor:'C. Ruíz',avance:42,cierre:'2026-08-19'},
    {id:'AI-2025-022',proceso:'Cuentas por Cobrar',cliente:'Constructora Montaña S.A.',estado:'planificacion',riesgo:'medio',auditor:'R. García',avance:8,cierre:'2026-09-05'}
  ];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normalize = s => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  function uid() { return 'm' + (globalThis.crypto?.randomUUID?.() || String(Date.now()) + String(Math.random()).slice(2)); }
  function sampleDetails(index) {
    if (index !== 0) return {};
    // Datos literales de ejemplo de la ficha Compras y Pagos del mockup.
    return {
      planificacion: {
        objetivo: 'Evaluar la efectividad del sistema de control interno del proceso de Compras y Pagos.',
        alcance: 'Ciclo de compras, aprobación, recepción y pagos. Período enero–junio 2026.',
        metodologia: 'NIA 315 / NIA 330 — enfoque basado en riesgos',
        horas: '120 horas', inicio:'2026-06-10',
        equipo: 'M. López — Encargado, C. Ruíz — Asistente'
      },
      riesgos: [
        ['Aprobación de compras','Compras sin autorización previa','4','5','Adecuado','Revisar aprobaciones'],
        ['Recepción de bienes','Recepción sin verificación física','3','4','Adecuado','Reforzar verificación'],
        ['Pago a proveedores','Pagos duplicados o ficticios','2','5','Parcial','Aplicar controles'],
        ['Segregación de funciones','Mismo usuario solicita y aprueba','4','4','No existe','Separar roles'],
        ['Gestión de contratos','Contratos vencidos sin renovación','2','3','Adecuado','Crear alertas'],
        ['Conciliación de cuentas por pagar','Diferencias no identificadas','3','3','Parcial','Conciliación mensual']
      ],
      controles: [
        ['Firma electrónica en órdenes de compra','Preventivo','Adecuado','Efectivo','Control operando correctamente'],
        ['Acta de recepción firmada','Detectivo','Adecuado','No efectivo','No aplica en 100% de casos'],
        ['Conciliación mensual de cuentas por pagar','Detectivo','Adecuado','Efectivo','Control operando correctamente'],
        ['Segregación entre solicitante y aprobador','Preventivo','No adecuado','No efectivo','Requiere diseño']
      ],
      hallazgos: [
        ['H-01','Ausencia de segregación entre solicitante y aprobador','Aprobación de compras','Significativo','Definir roles distintos','Gerencia de Compras','En proceso','2026-08-15'],
        ['H-02','Actas de recepción incompletas en el 30% de la muestra','Recepción de bienes','Moderado','Capacitar al personal','Jefe de Bodega','Pendiente','2026-09-01'],
        ['H-03','Retrasos en conciliación mensual','Cuentas por pagar','Leve','Automatizar conciliación','Contabilidad','Implementado','2026-07-20'],
        ['H-04','Contratos vencidos sin renovación','Gestión de contratos','Moderado','Crear alertas','Legal','Pendiente','2026-07-30'],
        ['H-05','Pagos sin validar proveedores','Pago a proveedores','Significativo','Validar padrón fiscal','Tesorería','Pendiente','2026-08-05'],
        ['H-06','Órdenes sin firma digital','Aprobación de compras','Leve','Bloquear flujo incompleto','TI','En proceso','2026-08-22']
      ],
      seguimiento: [
        ['H-01','Separar solicitante y aprobador en ERP','En proceso','40','Correo de solicitud a TI'],
        ['H-02','Capacitación al personal de bodega','Pendiente','0','—'],
        ['H-03','Automatizar conciliación mensual','Implementado','100','Reporte de conciliación']
      ],
      cronograma: [
        ['Planificación','M. López','2026-06-10','2026-06-17','Completada','100'],
        ['Evaluación de controles','C. Ruíz','2026-06-18','2026-07-05','Completada','100'],
        ['Pruebas sustantivas','M. López','2026-07-06','2026-07-26','En curso','85'],
        ['Hallazgos y validación','M. López','2026-07-27','2026-07-31','Pendiente','0'],
        ['Informe final','C. Ruíz','2026-08-01','2026-08-02','Pendiente','0']
      ],
      informe: 'Informe de Auditoría Interna\nCompras y Pagos — Distribuidora Pérez Hnos.\n\nSe evaluaron los principales procesos y controles internos. Se identificaron seis riesgos y seis hallazgos, con recomendaciones de fortalecimiento de la segregación de funciones, verificaciones y documentación.\n\nConclusión: dar seguimiento prioritario a los hallazgos significativos.'
    };
  }
  function initialData() { return SAMPLE_DATA.map((r,i) => ({...r, uid:'demo-'+i, details:sampleDetails(i)})); }
  function load() {
    try {
      const raw = localStorage.getItem(STORAGE);
      if (raw === null) return initialData();
      const value = JSON.parse(raw);
      if (!Array.isArray(value)) throw new Error('Formato inesperado');
      return value.filter(x => x && typeof x.uid === 'string').slice(0,1000)
        .map(x => ({...x,details: typeof x.details === 'object' && x.details !== null ? x.details : {}}));
    } catch (_) {
      $('iamSaveStatus').textContent = 'No se pudo leer el almacenamiento local. Se muestran ejemplos sin sobrescribirlos.';
      return initialData();
    }
  }
  let records = load();
  let sorting = {field:null,direction:1};
  let activeId = null;
  let activeTab = 'planificacion';
  // Confirmación de guardado VISIBLE, con resultado verificable en localStorage.
  const saveButtonOriginal = $('iamSaveAll').innerHTML;
  let saveButtonTimer = null;
  let dirty = false;
  function showFeedback(message, status) {
    const box=$('iamSaveFeedback');
    if (!box) return;
    box.hidden=false;
    box.className='iam-save-feedback iam-save-feedback--'+status;
    box.textContent=message;
  }
  function markDirty() {
    dirty=true;
    $('iamSaveStatus').textContent='Tienes cambios pendientes por guardar en este navegador.';
    showFeedback('● Cambios pendientes. Pulsa «Guardar cambios» para conservarlos al recargar.', 'warning');
    $('iamSaveAll').innerHTML=saveButtonOriginal;
  }
  function persist() {
    try {
      const json=JSON.stringify(records);
      localStorage.setItem(STORAGE,json);
      if (localStorage.getItem(STORAGE)!==json) throw new Error('No se pudo verificar el guardado');
      dirty=false;
      const hour=new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'});
      const text=`Cambios guardados correctamente a las ${hour} en este navegador. No se modificó ninguna auditoría real.`;
      $('iamSaveStatus').textContent=text;
      showFeedback('✓ '+text,'success');
      $('iamSaveAll').innerHTML='<i class="bi bi-check-circle-fill"></i> Guardado';
      clearTimeout(saveButtonTimer);
      saveButtonTimer=setTimeout(()=>$('iamSaveAll').innerHTML=saveButtonOriginal,2500);
      return true;
    } catch (error) {
      const text='No se pudo guardar en este navegador. Revisa el espacio disponible y la configuración de almacenamiento.';
      $('iamSaveStatus').textContent=text;
      showFeedback('✕ '+text,'error');
      $('iamSaveAll').innerHTML=saveButtonOriginal;
      return false;
    }
  }
  const fieldInput = (r, key, type='text', cls='') => `<input class="iam-input ${cls}" type="${type}" data-field="${key}" value="${esc(r[key])}" ${type==='number'?'min="0" max="100"':''} aria-label="${esc(key)}">`;
  const fieldSelect = (r, key, options) => `<select class="iam-input iam-select" data-field="${key}" aria-label="${esc(key)}">${Object.entries(options).map(([v,l])=>`<option value="${esc(v)}" ${r[key]===v?'selected':''}>${esc(l)}</option>`).join('')}</select>`;
  function dateDelta(iso) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(iso||''))) return null;
    const d = new Date(iso+'T12:00:00');
    if (Number.isNaN(d.getTime())) return null;
    const now = new Date(); now.setHours(12,0,0,0);
    return Math.round((d.getTime()-now.getTime())/86400000);
  }
  function getVisible() {
    const query=normalize($('iamSearch').value.trim());
    const status=$('iamFilterStatus').value, risk=$('iamFilterRisk').value, auditor=$('iamFilterAuditor').value;
    return records.filter(r => {
      const text=normalize([r.id,r.proceso,r.cliente,r.auditor].join(' '));
      return (!query || text.includes(query)) && (!status || r.estado===status) && (!risk || r.riesgo===risk) && (!auditor || r.auditor===auditor);
    }).sort((a,b) => {
      const key=sorting.field;
      const x=key==='avance'?Number(a[key]||0):normalize(a[key]);
      const y=key==='avance'?Number(b[key]||0):normalize(b[key]);
      return (x<y?-1:x>y?1:0)*sorting.direction;
    });
  }
  function updateKpis(rows) {
    const total=rows.length;
    const proc=rows.filter(r=>r.estado==='proceso').length;
    const high=rows.filter(r=>r.riesgo==='alto').length;
    const avg=total ? Math.round(rows.reduce((acc,r)=>acc+(Number(r.avance)||0),0)/total) : 0;
    const soon=rows.filter(r=>{const d=dateDelta(r.cierre);return r.estado!=='finalizada'&&d!==null&&d>=0&&d<=7;}).length;
    $('iamTotal').textContent=String(total);
    $('iamInProgress').textContent=String(proc);
    $('iamHighRisk').textContent=String(high);
    $('iamAvg').textContent=avg+'%';
    $('iamClosing').textContent=String(soon);
  }
  function updateAuditorOptions() {
    const current=$('iamFilterAuditor').value;
    const auditors=[...new Set(records.map(r=>(r.auditor||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es'));
    $('iamFilterAuditor').innerHTML='<option value="">Todos los auditores</option>'+auditors.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join('');
    if (auditors.includes(current)) $('iamFilterAuditor').value=current;
  }
  function render() {
    updateAuditorOptions();
    const rows=getVisible();
    $('iamRows').innerHTML=rows.map(r=>{
      const days=dateDelta(r.cierre);
      const label=r.estado==='finalizada'?'Finalizada':days===null?'Sin fecha':days<0?`Vencida · ${-days} días`:days===0?'Cierra hoy':`${days} días`;
      return `<tr data-uid="${esc(r.uid)}">
        <td>${fieldInput(r,'id','text','iam-id')}</td>
        <td>${fieldInput(r,'proceso')}</td>
        <td>${fieldInput(r,'cliente')}</td>
        <td>${fieldSelect(r,'estado',STATUSES)}</td>
        <td>${fieldSelect(r,'riesgo',RISKS)}</td>
        <td>${fieldInput(r,'auditor')}</td>
        <td><div class="iam-progress-input">${fieldInput(r,'avance','number','iam-num')}<span class="iam-percent">%</span></div><div class="iam-progress-track"><span style="width:${Math.min(100,Math.max(0,Number(r.avance)||0))}%"></span></div></td>
        <td>${fieldInput(r,'cierre','date')}<small class="iam-date-hint ${days!==null&&days<0&&r.estado!=='finalizada'?'iam-expired':''}">${esc(label)}</small></td>
        <td><div class="iam-row-actions"><button class="iam-btn iam-btn-primary iam-btn-sm" data-action="save" type="button">Guardar</button><button class="iam-btn iam-btn-outline iam-btn-sm" data-action="detail" type="button">Ver detalle <i class="bi bi-arrow-right"></i></button><button class="iam-icon-btn" data-action="delete" title="Eliminar registro manual" aria-label="Eliminar registro manual" type="button"><i class="bi bi-trash"></i> Eliminar</button></div></td>
      </tr>`;
    }).join('');
    $('iamEmpty').hidden=rows.length>0;
    $('iamResults').textContent=`${rows.length} de ${records.length} registros`;
    updateKpis(rows);
  }
  function applyField(el) {
    const row=el.closest('[data-uid]'); if(!row) return;
    const r=records.find(x=>x.uid===row.dataset.uid); if(!r) return;
    const key=el.dataset.field; if(!Object.hasOwn(r,key)) return;
    r[key]=key==='avance'?Math.min(100,Math.max(0,Number(el.value)||0)):el.value;
    // KPIs actualizados a partir de los mismos registros manuales, nunca desde Audit.
    updateKpis(getVisible());
    markDirty();
  }
  $('iamRows').addEventListener('input',e=>{if(e.target.matches('[data-field]'))applyField(e.target);});
  $('iamRows').addEventListener('change',e=>{if(e.target.matches('[data-field]')){applyField(e.target);render();}});
  $('iamRows').addEventListener('click',e=>{
    const button=e.target.closest('[data-action]'); if(!button) return;
    const row=button.closest('[data-uid]'); if(!row) return;
    const r=records.find(x=>x.uid===row.dataset.uid); if(!r) return;
    if(button.dataset.action==='save'){persist();render();}
    if(button.dataset.action==='detail')openDetail(r.uid);
    if(button.dataset.action==='delete'&&confirm(`¿Eliminar el registro manual «${r.id||r.proceso}»? Esta acción no elimina auditorías reales.`)){
      records=records.filter(x=>x.uid!==r.uid);persist();render();
    }
  });
  $('iamAddAudit').addEventListener('click',()=>{
    const r={uid:uid(),id:`AI-NUEVO-${records.length+1}`,proceso:'',cliente:'',estado:'planificacion',riesgo:'medio',auditor:'',avance:0,cierre:'',details:{}};
    records.unshift(r);persist();
    $('iamSearch').value='';$('iamFilterStatus').value='';$('iamFilterRisk').value='';$('iamFilterAuditor').value='';
    sorting={field:null,direction:1};render();
    const tr=$('iamRows').querySelector(`[data-uid="${CSS.escape(r.uid)}"]`);
    tr?.querySelector('[data-field="proceso"]')?.focus();
    tr?.scrollIntoView({behavior:'smooth',block:'nearest'});
  });
  $('iamSaveAll').addEventListener('click',()=>{persist();render();});
  $('iamRestore').addEventListener('click',()=>{
    if(!confirm('¿Restaurar los seis registros de ejemplo? Se reemplazarán los registros manuales guardados en ESTE navegador, sin tocar auditorías reales.'))return;
    records=initialData();persist();render();
  });
  ['iamSearch','iamFilterStatus','iamFilterRisk','iamFilterAuditor'].forEach(id=>{
    $(id).addEventListener('input',render);
    $(id).addEventListener('change',render);
  });
  document.querySelectorAll('[data-sort]').forEach(btn=>btn.addEventListener('click',()=>{
    const field=btn.dataset.sort;
    sorting=field===sorting.field?{field,direction:-sorting.direction}:{field,direction:1};render();
  }));
  // OOXML real (.xlsx) construido en el navegador. No usa CDN, no envía datos al servidor.
  // IMPORTANTE: en el XML de worksheet, autoFilter debe preceder a mergeCells (ISO/IEC 29500); Excel repara libros si están invertidos.
  function buildManualXlsx(sheets) {
    const xmlEsc = value => String(value ?? '')
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&apos;');
    const colName = n => {
      let result = '';
      for (let i = n; i > 0; i = Math.floor((i - 1) / 26)) result = String.fromCharCode(65 + (i - 1) % 26) + result;
      return result;
    };
    const validDate = text => {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
      const t = Date.parse(text + 'T00:00:00Z');
      return Number.isFinite(t) && new Date(t).toISOString().slice(0,10) === text;
    };
    function cellXml(value, row, col, style, asDate) {
      const ref = colName(col) + row;
      if (asDate && typeof value === 'string' && validDate(value)) {
        const serial = Math.round((Date.parse(value + 'T00:00:00Z') - Date.UTC(1899,11,30)) / 86400000);
        return `<c r="${ref}" s="4" t="n"><v>${serial}</v></c>`;
      }
      if (typeof value === 'number' && Number.isFinite(value)) return `<c r="${ref}" s="${style}" t="n"><v>${value}</v></c>`;
      const content = xmlEsc(String(value ?? '').slice(0,32767));
      return `<c r="${ref}" s="${style}" t="inlineStr"><is><t xml:space="preserve">${content}</t></is></c>`;
    }
    function sheetXml(sheet) {
      const rows = Array.isArray(sheet.rows) ? sheet.rows : [];
      const headers = sheet.headers;
      const count = Math.max(headers.length, ...(rows.map(x => x.length)), 2);
      const lastCol = colName(count);
      const widths = sheet.widths || [];
      const columns = Array.from({length:count},(_,i)=>{
        const width = Math.max(9, Math.min(65, Number(widths[i]) || 20));
        return `<col min="${i+1}" max="${i+1}" width="${width}" customWidth="1"/>`;
      }).join('');
      const dataRows = rows.map((r,index)=>{
        const row=index+5;
        const cells=r.map((v,i)=>cellXml(v,row,i+1,index%2===0?0:2,(sheet.dateCols||[]).includes(i))).join('');
        return `<row r="${row}">${cells}</row>`;
      }).join('');
      const headersXml = headers.map((v,i)=>cellXml(v,4,i+1,1,false)).join('');
      const lastRow=4+rows.length;
      return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<dimension ref="A1:${lastCol}${lastRow}"/>
<sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/><selection pane="bottomLeft" activeCell="A5" sqref="A5"/></sheetView></sheetViews>
<sheetFormatPr defaultRowHeight="17"/>
<cols>${columns}</cols>
<sheetData>
<row r="1" ht="32" customHeight="1">${cellXml(sheet.title,1,1,1,false)}</row>
<row r="2" ht="24" customHeight="1">${cellXml(sheet.subtitle || 'Datos manuales · AuditaPro',2,1,3,false)}</row>
<row r="4" ht="27" customHeight="1">${headersXml}</row>
${dataRows}</sheetData>
<autoFilter ref="A4:${lastCol}${Math.max(4,lastRow)}"/>
<mergeCells count="2"><mergeCell ref="A1:${lastCol}1"/><mergeCell ref="A2:${lastCol}2"/></mergeCells>
<pageMargins left="0.3" right="0.3" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>
</worksheet>`;
    }
    const styleXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/></numFmts>
<fonts count="3"><font><sz val="11"/><name val="Aptos"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Aptos"/></font><font><b/><sz val="11"/><color rgb="FF1E3A5F"/><name val="Aptos"/></font></fonts>
<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEFF6FF"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="5">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1"/>
<xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>`;
    const book = sheets.map((s,i)=>`<sheet name="${xmlEsc(s.name)}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join('');
    const rels = sheets.map((s,i)=>`<Relationship Id="rId${i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i+1}.xml"/>`).join('')+
      `<Relationship Id="rId${sheets.length+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>`;
    const overrides = sheets.map((s,i)=>`<Override PartName="/xl/worksheets/sheet${i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('');
    const files = [
      ['[Content_Types].xml',`<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>${overrides}</Types>`],
      ['_rels/.rels',`<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`],
      ['xl/workbook.xml',`<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${book}</sheets></workbook>`],
      ['xl/_rels/workbook.xml.rels',`<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${rels}</Relationships>`],
      ['xl/styles.xml',styleXml],
      ...sheets.map((s,i)=>[`xl/worksheets/sheet${i+1}.xml`,sheetXml(s)])
    ];
    const enc = new TextEncoder();
    let crcTable;
    function crc32(bytes) {
      if (!crcTable) crcTable = Array.from({length:256},(_,i)=>{
        let n=i;
        for(let j=0;j<8;j++) n=n&1?0xEDB88320^(n>>>1):n>>>1;
        return n>>>0;
      });
      let crc=0xFFFFFFFF;
      for (const byte of bytes) crc=crcTable[(crc^byte)&255]^(crc>>>8);
      return (crc^0xFFFFFFFF)>>>0;
    }
    const localParts=[], centers=[];
    let offset=0;
    for(const [filename,text] of files){
      const filenameBytes=enc.encode(filename), content=enc.encode(text), crc=crc32(content);
      const local=new Uint8Array(30+filenameBytes.length), lv=new DataView(local.buffer);
      lv.setUint32(0,0x04034b50,true);lv.setUint16(4,20,true);lv.setUint16(6,0x0800,true);
      lv.setUint32(14,crc,true);lv.setUint32(18,content.length,true);lv.setUint32(22,content.length,true);
      lv.setUint16(26,filenameBytes.length,true);local.set(filenameBytes,30);
      localParts.push(local,content);
      const center=new Uint8Array(46+filenameBytes.length), cv=new DataView(center.buffer);
      cv.setUint32(0,0x02014b50,true);cv.setUint16(4,20,true);cv.setUint16(6,20,true);
      cv.setUint16(8,0x0800,true);cv.setUint32(16,crc,true);
      cv.setUint32(20,content.length,true);cv.setUint32(24,content.length,true);
      cv.setUint16(28,filenameBytes.length,true);cv.setUint32(42,offset,true);
      center.set(filenameBytes,46);centers.push(center);
      offset+=local.length+content.length;
    }
    const centralLength=centers.reduce((n,x)=>n+x.length,0);
    const end=new Uint8Array(22), ev=new DataView(end.buffer);
    ev.setUint32(0,0x06054b50,true);
    ev.setUint16(8,files.length,true);ev.setUint16(10,files.length,true);
    ev.setUint32(12,centralLength,true);ev.setUint32(16,offset,true);
    return new Blob([...localParts,...centers,end],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
  }
  function downloadXlsx(filename, sheets) {
    const blob=buildManualXlsx(sheets), url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),6000);
  }

  function visibleSummary(rows) {
    return [
      ['Registros exportados',rows.length],
      ['En proceso',rows.filter(r=>r.estado==='proceso').length],
      ['Riesgo alto',rows.filter(r=>r.riesgo==='alto').length],
      ['Avance promedio (%)',rows.length?Math.round(rows.reduce((sum,r)=>sum+(Number(r.avance)||0),0)/rows.length):0],
      ['Cierran en 7 días',rows.filter(r=>{const d=dateDelta(r.cierre);return r.estado!=='finalizada'&&d!==null&&d>=0&&d<=7;}).length],
      ['Origen','Dashboard manual de Auditoría Interna; no consulta el sistema de proyectos']
    ];
  }
  $('iamExport').addEventListener('click',()=>{
    const rows=getVisible();
    try {
      downloadXlsx('Auditoria_Interna_Manual.xlsx',[
        {name:'Listado',title:'Auditorías Internas · Listado manual',
         subtitle:'Datos editados en esta pantalla · AuditaPro',
         headers:['ID','Proceso / Área','Cliente','Estado','Riesgo','Auditor asignado','Avance (%)','Cierre estimado'],
         rows:rows.map(r=>[r.id,r.proceso,r.cliente,STATUSES[r.estado]||r.estado,RISKS[r.riesgo]||r.riesgo,r.auditor,Number(r.avance)||0,r.cierre]),
         widths:[18,33,33,20,18,30,17,19],dateCols:[7]},
        {name:'Resumen',title:'Resumen de Auditoría Interna',
         subtitle:'Indicadores calculados exclusivamente de los registros exportados',
         headers:['Indicador','Valor'],rows:visibleSummary(rows),widths:[35,64]}
      ]);
    } catch(error){
      showFeedback('✕ No se pudo generar el libro de Excel. '+(error?.message||''),'error');
    }
  });

  function active() {return records.find(r=>r.uid===activeId);}
  function detailData(r){if(!r.details || typeof r.details!=='object')r.details={};return r.details;}
  const PLAN=[['objetivo','Objetivo de la auditoría'],['alcance','Alcance'],['metodologia','Metodología'],['horas','Horas presupuestadas'],['inicio','Fecha de inicio'],['equipo','Equipo asignado']];
  function openDetail(id){
    activeId=id;activeTab='planificacion';
    $('iamListView').hidden=true;$('iamDetailView').hidden=false;
    renderDetail();window.scrollTo({top:0,behavior:'smooth'});
  }
  function renderDetail(){
    const r=active();if(!r){closeDetail();return;}
    $('iamDetailTitle').textContent=`${r.id} · ${r.proceso||'Nuevo encargo'}`;
    $('iamDetailSubtitle').textContent=`${r.cliente||'Sin cliente'} · ${STATUSES[r.estado]||''} · ${RISKS[r.riesgo]||''}`;
    $('iamTabs').innerHTML=TABS.map(([key,label])=>`<button type="button" role="tab" aria-selected="${key===activeTab}" class="iam-tab ${key===activeTab?'active':''}" data-tab="${key}">${esc(label)}</button>`).join('');
    const d=detailData(r);
    if(activeTab==='planificacion'){
      const vals=d.planificacion||{};
      $('iamDetailContent').innerHTML=`<div class="iam-detail-note">✎ Todos los campos de esta ficha son manuales. No afectan los papeles de trabajo ni la planificación real.</div><div class="iam-form-grid">${PLAN.map(([field,label])=>`<label class="iam-field ${['objetivo','alcance','equipo'].includes(field)?'iam-wide':''}"><span>${label}</span>${['objetivo','alcance'].includes(field)?`<textarea data-plan="${field}" rows="3">${esc(vals[field]||'')}</textarea>`:`<input data-plan="${field}" type="text" value="${esc(vals[field]||'')}">`}</label>`).join('')}</div>`;
    } else if(activeTab==='informe'){
      $('iamDetailContent').innerHTML=`<div class="iam-detail-note">Informe manual independiente. El texto se guarda en este navegador.</div><label class="iam-field iam-wide"><span>Informe Final</span><textarea data-informe rows="14" placeholder="Escribe aquí el informe...">${esc(d.informe||'')}</textarea></label>`;
    } else {
      const headers=FIELDS[activeTab];if(!Array.isArray(d[activeTab]))d[activeTab]=[];
      $('iamDetailContent').innerHTML=`<div class="iam-detail-note">✎ Tabla manual independiente de los modelos de auditoría. Usa Añadir fila y Guardar ficha.</div><div class="iam-actions iam-section-actions"><button type="button" class="iam-btn iam-btn-primary" id="iamAddDetailRow"><i class="bi bi-plus-lg"></i> Añadir fila</button></div><div class="iam-table-wrap"><table class="iam-table iam-detail-table"><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}<th>Acciones</th></tr></thead><tbody>${d[activeTab].map((row,index)=>`<tr data-detail-index="${index}">${headers.map((h,col)=>`<td><input class="iam-input" data-detail-field="${col}" value="${esc(row[col]||'')}" aria-label="${esc(h)}"></td>`).join('')}<td><button type="button" data-detail-remove="${index}" class="iam-icon-btn" aria-label="Eliminar fila manual"><i class="bi bi-trash"></i></button></td></tr>`).join('')}</tbody></table></div>${d[activeTab].length?'':'<p class="iam-muted">Aún no hay registros en esta sección.</p>'}`;
    }
  }
  function updateDetailField(el){
    const r=active();if(!r)return;const d=detailData(r);
    if(el.matches('[data-plan]')) {if(!d.planificacion)d.planificacion={};d.planificacion[el.dataset.plan]=el.value;}
    if(el.matches('[data-informe]'))d.informe=el.value;
    if(el.matches('[data-detail-field]')) {const row=el.closest('[data-detail-index]');const i=Number(row?.dataset.detailIndex);const col=Number(el.dataset.detailField);if(d[activeTab]?.[i])d[activeTab][i][col]=el.value;}
    markDirty();
  }
  $('iamDetailContent').addEventListener('input',e=>updateDetailField(e.target));
  $('iamDetailContent').addEventListener('click',e=>{
    const r=active();if(!r)return;const d=detailData(r);
    if(e.target.closest('#iamAddDetailRow')){d[activeTab].push(FIELDS[activeTab].map(()=>''));renderDetail();}
    const remove=e.target.closest('[data-detail-remove]');if(remove){
      const index=Number(remove.dataset.detailRemove);d[activeTab].splice(index,1);renderDetail();
    }
  });
  $('iamTabs').addEventListener('click',e=>{const tab=e.target.closest('[data-tab]');if(tab){activeTab=tab.dataset.tab;renderDetail();}});
  function closeDetail(){$('iamDetailView').hidden=true;$('iamListView').hidden=false;activeId=null;render();}
  $('iamBack').addEventListener('click',()=>{persist();closeDetail();});
  $('iamSaveDetail').addEventListener('click',()=>{persist();renderDetail();});
  $('iamExportDetail').addEventListener('click',()=>{
    const r=active();if(!r)return;const d=detailData(r);
    const data=[['Ficha manual','Valor'],['ID',r.id],['Proceso / Área',r.proceso],['Cliente',r.cliente],['Estado',STATUSES[r.estado]],['Riesgo',RISKS[r.riesgo]],['Auditor',r.auditor],['Avance (%)',r.avance],['Cierre',r.cierre]];
    TABS.forEach(([key,label])=>{
      data.push(['',''],[label,'']);
      if(key==='planificacion')PLAN.forEach(([field,name])=>data.push([name,d.planificacion?.[field]||'']));
      else if(key==='informe')data.push(['Texto',d.informe||'']);
      else(d[key]||[]).forEach(item=>data.push([FIELDS[key].join(' | '),item.join(' | ')]));
    });
    const sheets=[{name:'Ficha',title:'Ficha de Auditoría Interna · '+r.id,
      subtitle:'Registro manual, separado de las auditorías reales',
      headers:['Campo','Valor'],rows:data.slice(1),widths:[36,65]}];
    TABS.forEach(([key,label])=>{
      if(key==='planificacion') sheets.push({name:'Planificacion',title:label,
        headers:['Dato','Valor'],rows:PLAN.map(([field,name])=>[name,d.planificacion?.[field]||'']),widths:[35,65]});
      else if(key==='informe') sheets.push({name:'Informe Final',title:label,
        headers:['Texto del informe'],rows:[[d.informe||'']],widths:[65]});
      else sheets.push({name:({'riesgos':'Riesgos','controles':'Controles','hallazgos':'Hallazgos',
        'seguimiento':'Seguimiento','cronograma':'Cronograma'})[key],title:label,
        headers:FIELDS[key],rows:d[key]||[],widths:FIELDS[key].map(()=>27)});
    });
    try {downloadXlsx('Ficha_Auditoria_Interna_'+String(r.id).replace(/[^a-zA-Z0-9_-]/g,'_')+'.xlsx',sheets);}
    catch(error){showFeedback('✕ No se pudo exportar la ficha Excel: '+(error?.message||''),'error');}
  });
  render();
})();
