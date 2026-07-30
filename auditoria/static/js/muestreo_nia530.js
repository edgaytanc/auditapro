/* Lógica del módulo Muestreo NIA 530.
   Lee el contexto dinámico desde window.MUESTREO_CTX (mismo patrón que
   window.AUDIT_CTX en auditoria_detalle.js). */

const {
    audit_id: muestreoAuditId,
    calcular_url: muestreoCalcularUrl,
    descargar_url: muestreoDescargarUrl,
    importar_url: muestreoImportarUrl,
    formato_url: muestreoFormatoUrl
} = window.MUESTREO_CTX || {
    audit_id: null, calcular_url: null, descargar_url: null,
    importar_url: null, formato_url: null
};

let metodoActivo = 'aleatorio_simple';
let ultimoCalculo = null; // { metodo, parametros } del último cálculo exitoso

const TITULOS_METODO = {
    aleatorio_simple: ['Aleatorio Simple', 'NIA 530', 'Para cuentas donde cada partida tiene similar probabilidad de error (CxC, inversiones, gastos varios).'],
    estratificado: ['Estratificado', 'NIA 530', 'Cuando la población tiene subgrupos de valor muy distinto (alto / medio / bajo valor).'],
    mus: ['Monetario (MUS) — Unidad Monetaria', 'NIA 530', 'Para saldos en moneda: bancos, inventarios, cuentas donde el riesgo crece con el monto.'],
    atributos: ['Por Atributos — Pruebas de Controles', 'NIA 530', 'Para evaluar si un control interno operó de forma efectiva durante el periodo.'],
    criterio: ['Por Criterio', 'Selección dirigida', 'Selección dirigida de partidas inusuales o significativas, no es muestreo estadístico.']
};

function csrfToken() {
    const input = document.querySelector('#muestreoCsrf [name=csrfmiddlewaretoken]');
    return input ? input.value : '';
}

function valorNumero(id) {
    const elemento = document.getElementById(id);
    return elemento && elemento.value !== '' ? Number(elemento.value) : null;
}

function valorSemilla(id) {
    const elemento = document.getElementById(id);
    return elemento && elemento.value !== '' ? Number(elemento.value) : null;
}

// ---------------------------------------------------------------------------
// Cambio de método
// ---------------------------------------------------------------------------

document.querySelectorAll('.metodo-btn').forEach(boton => {
    boton.addEventListener('click', () => {
        document.querySelectorAll('.metodo-btn').forEach(b => b.classList.remove('active'));
        boton.classList.add('active');
        metodoActivo = boton.dataset.metodo;

        document.querySelectorAll('.mform').forEach(formulario => formulario.style.display = 'none');
        document.getElementById('form-' + metodoActivo).style.display =
            metodoActivo === 'criterio' ? 'block' : 'grid';

        const [titulo, etiqueta, pista] = TITULOS_METODO[metodoActivo];
        document.getElementById('formTitle').innerHTML =
            titulo + ' <span class="nia-tag">' + etiqueta + '</span>';
        document.getElementById('formHint').textContent = pista;

        ocultarResultados();
    });
});

function ocultarResultados() {
    ultimoCalculo = null;
    document.getElementById('resultadoPanel').classList.remove('show');
    document.getElementById('descargaCard').style.display = 'none';
    const cajaError = document.getElementById('errorBox');
    cajaError.style.display = 'none';
    cajaError.textContent = '';
}

// ---------------------------------------------------------------------------
// Recolección de parámetros por método
// ---------------------------------------------------------------------------

// Por Criterio: el detalle transaccional puede venir pegado en el textarea
// (N.º Documento [tab] Descripción [tab] Fecha [tab] Monto). Se tolera el
// separador tabulador y también el punto y coma.
function recolectarPartidasPegadas() {
    const texto = (document.getElementById('c_pegado') || {}).value || '';
    const partidas = [];
    texto.split('\n').forEach(linea => {
        if (!linea.trim()) { return; }
        const celdas = linea.split(linea.indexOf('\t') >= 0 ? '\t' : ';');
        if (celdas.length < 4) { return; }
        const monto = parseFloat(String(celdas[3]).replace(/[^\d.,-]/g, '').replace(/,/g, ''));
        if (isNaN(monto)) { return; }
        partidas.push({
            documento: (celdas[0] || '').trim(),
            descripcion: (celdas[1] || '').trim(),
            fecha: (celdas[2] || '').trim(),
            monto: monto
        });
    });
    return partidas;
}

function totalPegado() {
    return recolectarPartidasPegadas().reduce((suma, p) => suma + p.monto, 0);
}

function recolectarParametros() {
    if (metodoActivo === 'aleatorio_simple') {
        return {
            nivel_confianza: valorNumero('s_conf'),
            tolerancia: valorNumero('s_tol'),
            poblacion: valorNumero('s_N'),
            materialidad: valorNumero('s_mat'),
            sigma: valorNumero('s_sigma'),
            semilla: valorSemilla('s_semilla')
        };
    }
    if (metodoActivo === 'estratificado') {
        return {
            nivel_confianza: valorNumero('e_conf'),
            tolerancia: valorNumero('e_tol'),
            materialidad: valorNumero('e_mat'),
            sigma: valorNumero('e_sigma'),
            n1: valorNumero('e_n1'),
            n2: valorNumero('e_n2'),
            n3: valorNumero('e_n3'),
            semilla: valorSemilla('e_semilla')
        };
    }
    if (metodoActivo === 'mus') {
        return {
            nivel_confianza: valorNumero('m_conf'),
            valor_libros: valorNumero('m_bv'),
            error_tolerable: valorNumero('m_te'),
            error_esperado: valorNumero('m_ea'),
            semilla: valorSemilla('m_semilla')
        };
    }
    if (metodoActivo === 'atributos') {
        return {
            nivel_confianza: valorNumero('a_conf'),
            desviacion_tolerable: valorNumero('a_ef'),
            tasa_esperada: valorNumero('a_p'),
            poblacion: valorNumero('a_N'),
            semilla: valorSemilla('a_semilla')
        };
    }
    // criterio: criterios de monto sobre el detalle transaccional
    const parametros = {
        porcentaje_examinar: valorNumero('c_pct'),
        monto_mayor: valorNumero('c_mayor'),
        monto_menor: valorNumero('c_menor')
    };
    const total = document.getElementById('c_total');
    if (total && total.value !== '') {
        parametros.valor_total = Number(total.value);
    }
    // En modo manual (sin Excel) las partidas van dentro de los parámetros
    const pegadas = recolectarPartidasPegadas();
    if (pegadas.length) {
        parametros.partidas = pegadas;
    }
    return parametros;
}

// ---------------------------------------------------------------------------
// Cálculo (POST JSON con encabezado CSRF)
// ---------------------------------------------------------------------------

document.getElementById('calcularBtn').addEventListener('click', () => {
    const parametros = recolectarParametros();
    const cajaError = document.getElementById('errorBox');
    cajaError.style.display = 'none';

    fetch(muestreoCalcularUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken()
        },
        body: JSON.stringify({ metodo: metodoActivo, parametros: parametros })
    })
        .then(respuesta => respuesta.json())
        .then(datos => {
            if (datos.success) {
                ultimoCalculo = { metodo: metodoActivo, parametros: parametros };
                renderResultado(datos.data);
            } else {
                mostrarError(datos.error || 'Error al calcular la muestra.');
            }
        })
        .catch(() => mostrarError('Error inesperado de comunicación con el servidor.'));
});

function mostrarError(mensaje) {
    const cajaError = document.getElementById('errorBox');
    cajaError.textContent = mensaje;
    cajaError.style.display = 'block';
    document.getElementById('resultadoPanel').classList.remove('show');
    document.getElementById('descargaCard').style.display = 'none';
}

// ---------------------------------------------------------------------------
// Render de resultados
// ---------------------------------------------------------------------------

const LIMITE_FILAS_SELECCION = 100;

function renderResultado(data) {
    const grid = document.getElementById('resultadoGrid');
    grid.innerHTML = '';
    Object.entries(data.resultados).forEach(([etiqueta, valor]) => {
        const tarjeta = document.createElement('div');
        tarjeta.className = 'stat';
        tarjeta.innerHTML = '<div class="label"></div><div class="value"></div>';
        tarjeta.querySelector('.label').textContent = etiqueta;
        tarjeta.querySelector('.value').textContent = valor;
        grid.appendChild(tarjeta);
    });

    document.getElementById('formulaBox').textContent = 'Fórmula: ' + data.formula_texto;
    document.getElementById('semillaBox').textContent = data.semilla !== null
        ? 'Semilla de selección utilizada: ' + data.semilla + ' (consérvela para reproducir la muestra — evidencia NIA 530).'
        : 'Selección dirigida: no se utiliza semilla aleatoria.';

    // Tabla de selección (se muestran las primeras filas; la descarga trae todas).
    // Si la muestra se generó desde el Excel de datos, se listan las partidas reales.
    const tabla = document.getElementById('tablaSeleccion');
    const detalle = data.detalle_partidas;
    const filas = detalle || data.seleccion;

    // Cuando la selección explica por qué entró cada partida (100 %,
    // sistemática, complementaria) se muestra esa columna.
    const conCriterio = detalle && filas.some(item => item.marca);

    let filasHtml;
    if (detalle) {
        filasHtml = '<tr><th>Nº</th><th>N.º Documento</th><th>Descripción</th>' +
            '<th>Fecha</th><th>Monto</th>' +
            (conCriterio ? '<th>Criterio de selección</th>' : '') + '</tr>';
    } else {
        filasHtml = '<tr><th>Nº</th><th>Elemento seleccionado</th></tr>';
    }

    filas.slice(0, LIMITE_FILAS_SELECCION).forEach(item => {
        const fila = document.createElement('tr');
        let celdas;
        if (detalle) {
            celdas = [item.no, item.documento, item.descripcion, item.fecha, item.monto];
            if (conCriterio) { celdas.push(item.marca || ''); }
        } else {
            celdas = [item.numero, item.elemento];
        }
        celdas.forEach(valor => {
            const celda = document.createElement('td');
            celda.textContent = valor;
            fila.appendChild(celda);
        });
        filasHtml += fila.outerHTML;
    });
    tabla.innerHTML = filasHtml;

    const nota = document.getElementById('notaSeleccion');
    if (filas.length > LIMITE_FILAS_SELECCION) {
        nota.textContent = '… y ' + (filas.length - LIMITE_FILAS_SELECCION) +
            ' elementos más (incluidos completos en la descarga).';
    } else {
        nota.textContent = '';
    }

    document.getElementById('resultadoPanel').classList.add('show');
    document.getElementById('descargaCard').style.display = 'block';
}

// ---------------------------------------------------------------------------
// Descargas
// ---------------------------------------------------------------------------

// El detalle transaccional puede tener miles de partidas: nunca viaja en la
// URL de descarga. El servidor ya guardó la muestra calculada en la sesión y la
// reconoce con el resto de los parámetros.
function parametrosParaUrl(parametros) {
    const copia = Object.assign({}, parametros || {});
    delete copia.partidas;
    return copia;
}

function descargarMuestreo(formato) {
    if (!ultimoCalculo) {
        mostrarError('Primero calcule la muestra antes de descargar el papel de trabajo.');
        return;
    }
    const url = muestreoDescargarUrl +
        '?metodo=' + encodeURIComponent(ultimoCalculo.metodo) +
        '&parametros=' + encodeURIComponent(
            JSON.stringify(parametrosParaUrl(ultimoCalculo.parametros))) +
        '&formato=excel';
    window.location.href = url;
}

document.querySelectorAll('.dl-btn[data-formato]').forEach(boton => {
    boton.addEventListener('click', () => descargarMuestreo(boton.dataset.formato));
});

// ---------------------------------------------------------------------------
// Método Por Criterio: Valor Monetario Total desde el detalle pegado
// ---------------------------------------------------------------------------

const botonTotalCriterio = document.getElementById('c_totalBtn');
if (botonTotalCriterio) {
    botonTotalCriterio.addEventListener('click', () => {
        const total = totalPegado();
        if (!total) {
            estadoImportacion(
                'Pegue el detalle transaccional (o suba el Excel) para calcular el ' +
                'Valor Monetario Total.', 'error');
            return;
        }
        document.getElementById('c_total').value = Math.round(total * 100) / 100;
        estadoImportacion(
            'Valor Monetario Total calculado desde el detalle pegado: ' +
            total.toLocaleString('es-GT', { minimumFractionDigits: 2 }), 'ok');
    });
}

// ---------------------------------------------------------------------------
// Importación del Excel de datos (mayor auxiliar)
//
// El archivo NO se guarda en el sistema: se sube, el servidor lo lee en
// memoria, genera la muestra y lo descarta. Para repetir el cálculo hay que
// volver a subirlo.
// ---------------------------------------------------------------------------

function estadoImportacion(mensaje, tipo) {
    const caja = document.getElementById('importEstado');
    if (!caja) return;
    caja.textContent = mensaje || '';
    caja.className = 'import-estado' + (tipo ? ' ' + tipo : '');
}

// Parámetros que se deducen del archivo por método → id del campo del
// formulario. Al generar la muestra DESDE EL ARCHIVO, estos campos se
// deducen del propio Excel (población, desviación y valor en libros): el
// valor precargado del formulario no debe pisar los datos reales del archivo.
const CAMPOS_DERIVABLES_ARCHIVO = {
    aleatorio_simple: { poblacion: 's_N', sigma: 's_sigma' },
    estratificado: { sigma: 'e_sigma' },
    mus: { valor_libros: 'm_bv' },
    atributos: { poblacion: 'a_N' },
    // Por Criterio: el Valor Monetario Total sale de la suma del archivo
    criterio: { valor_total: 'c_total' }
};

function importarDatosMuestreo() {
    const entrada = document.getElementById('archivoDatos');
    if (!entrada || !entrada.files.length) {
        estadoImportacion('Seleccione primero el Excel de datos (mayor auxiliar).', 'error');
        return;
    }

    // Los parámetros derivables se toman SIEMPRE del archivo subido
    const parametros = recolectarParametros();
    const camposDerivables = CAMPOS_DERIVABLES_ARCHIVO[metodoActivo] || {};
    Object.keys(camposDerivables).forEach(clave => { parametros[clave] = null; });

    const formData = new FormData();
    formData.append('archivo_datos', entrada.files[0]);
    formData.append('metodo', metodoActivo);
    formData.append('parametros', JSON.stringify(parametros));

    estadoImportacion('Leyendo el archivo y generando la muestra…', '');
    document.getElementById('errorBox').style.display = 'none';

    fetch(muestreoImportarUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken() },
        body: formData
    })
        .then(respuesta => respuesta.json())
        .then(datos => {
            if (!datos.success) {
                estadoImportacion('', '');
                mostrarError(datos.error || 'No se pudo procesar el archivo.');
                return;
            }
            ultimoCalculo = {
                metodo: metodoActivo,
                parametros: datos.parametros_aplicados
            };
            // Reflejar en el formulario los valores deducidos del archivo,
            // para que el auditor VEA la población/desviación/valor en libros
            // con los que realmente se generó la muestra.
            const aplicados = datos.parametros_aplicados || {};
            Object.entries(camposDerivables).forEach(([clave, idCampo]) => {
                const campo = document.getElementById(idCampo);
                if (campo && aplicados[clave] !== undefined && aplicados[clave] !== null) {
                    campo.value = Math.round(aplicados[clave] * 100) / 100;
                }
            });
            const origen = datos.origen || {};
            estadoImportacion(
                `${datos.mensaje} · Cuenta: ${origen.cuenta || 'no indicada'} · ` +
                `Población (N): ${origen.partidas}`,
                'ok'
            );
            renderResultado(datos.data);
            // El archivo ya se descartó en el servidor; se limpia el selector
            entrada.value = '';
        })
        .catch(() => {
            estadoImportacion('', '');
            mostrarError('Error inesperado al subir el archivo de datos.');
        });
}

function descargarFormatoDatos() {
    if (muestreoFormatoUrl) window.location.href = muestreoFormatoUrl;
}

const botonImportar = document.getElementById('importarDatosBtn');
if (botonImportar) botonImportar.addEventListener('click', importarDatosMuestreo);

const botonFormato = document.getElementById('formatoDatosBtn');
if (botonFormato) botonFormato.addEventListener('click', descargarFormatoDatos);
