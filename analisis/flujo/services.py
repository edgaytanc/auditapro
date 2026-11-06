"""Flujo de hallazgos de la fase 2: enviar a papel de trabajo → revisión → aprobación → hallazgos finales → informe.

Cada hallazgo conserva su ``finding_id``; H-01, HF-01 o «CRÍTICO 1» son etiquetas. Todo es idempotente (huella) y versionado
(los archivos originales no se tocan), y cada acción deja registro encadenado en ``BitacoraProyecto``.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from audits.models import Audit

from ..models import (
    ArchivoProyecto,
    BitacoraProyecto,
    ColocacionHallazgo,
    CorridaAnalisis,
    EvidenciaHallazgo,
    Hallazgo,
    HallazgoAnalisis,
    RevisionHallazgo,
)
from ..services import accessible_audits, role_name
from . import config, docx_informe, xl, xl2

PLANTILLAS = Path(__file__).parent / "plantillas"
ESTATICO = Path(settings.BASE_DIR) / "static"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class FlujoError(Exception):
    """Regla del flujo incumplida (se muestra tal cual al usuario)."""


# ----------------------------------------------------------------------------- proyecto, roles, individual
def modulo_de(audit: Audit) -> str:
    tipo = (audit.tipoAuditoria or "F").upper()
    return tipo if tipo in ("F", "I", "R") else "F"


def miembros(audit: Audit) -> set[int]:
    return {audit.audit_manager_id, *audit.assigned_users.values_list("pk", flat=True)}


def es_individual(audit: Audit) -> bool:
    """Auditoría individual: un solo usuario en Gestionar Auditores (el jefe, sin auditores aparte)."""
    return len(miembros(audit)) == 1


def es_jefe(user, audit: Audit) -> bool:
    return bool(user.is_staff or (role_name(user) == "audit_manager" and audit.audit_manager_id == user.pk))


def puede_decidir(user, audit: Audit) -> bool:
    return es_jefe(user, audit) or (es_individual(audit) and user.pk in miembros(audit))


def _acceso(user, audit: Audit) -> None:
    if not accessible_audits(user).filter(pk=audit.pk).exists():
        raise FlujoError("No tiene acceso a esta auditoría.")


def _log(audit, user, accion, entidad="", entidad_id="", antes=None, despues=None):
    return BitacoraProyecto.registrar(audit, user, accion, entidad, entidad_id, antes, despues,
                                      individual=es_individual(audit) and bool(user and user.pk in miembros(audit)))


def etiqueta_estado(h: Hallazgo) -> str:
    if h.estado == config.INCLUIDO and h.modulo == "R":
        return "Comunicado"
    return config.ETIQUETA_ESTADO.get(h.estado, h.estado)


def nombre_destino(h: Hallazgo) -> str:
    if h.modulo == "F":
        return config.cuentas_fin().get(h.cuenta, {}).get("nombre", h.cuenta)
    if h.modulo == "I":
        return config.areas_ai().get(h.area, {}).get("nombre", h.area)
    return h.area or ""


# ----------------------------------------------------------------------------- archivos versionados
def _base_estatica(*candidatos: str) -> Path | None:
    for c in candidatos:
        p = ESTATICO / c
        if p.is_file():
            return p
    return None


def ruta_base(audit: Audit, clave: str, destino: str = "") -> Path:
    """Plantilla original de cada archivo del flujo. Sale de ``static/templates_base_*`` y, si falta, de la copia incluida."""
    mod = modulo_de(audit)
    tipo = clave.split(":")[0]
    if mod == "F":
        cta = config.cuentas_fin().get(destino, {})
        if tipo in ("hallazgos", "evidencias"):
            f = cta.get("h" if tipo == "hallazgos" else "e", "")
            p = _base_estatica(f"templates_base_financiera/{config.RAIZ_PRUEBAS_FIN}/{cta.get('carpeta', '')}/{f}") if f else None
            return p or PLANTILLAS / ("Hallazgos.xlsx" if tipo == "hallazgos" else "Evidencias.xlsx")
        fin = "templates_base_financiera/5 FINALIZACION"
        if tipo == "revision":
            return _base_estatica(f"{fin}/5 FINALIZACION/3 Revision_Hallazgos.xlsx") or _falta(clave)
        if tipo == "finales":
            return _base_estatica(f"{fin}/5 FINALIZACION/4 Hallazgos_Finales.xlsx") or _falta(clave)
        if tipo == "informe":
            return _base_estatica(f"{fin}/6 INFORME Y DICTAMENES/1 INFORME_AUDITORIA_FINANCIERA.docx") or _falta(clave)
    if mod == "I":
        if tipo in ("hallazgos", "evidencias"):
            return PLANTILLAS / ("Hallazgos.xlsx" if tipo == "hallazgos" else "Evidencias.xlsx")
        if tipo == "borrador":
            return PLANTILLAS / "Borrador_Informe.xlsx"
        if tipo == "informe":
            a = config.areas_ai().get(destino, {})
            return _base_estatica(f"templates_base_interna/{config.CARPETA_INFORMES_AI}/{a.get('informe', '')}") or PLANTILLAS / "(sin_base)"
    if mod == "R":
        if tipo in ("hallazgos", "evidencias"):
            return PLANTILLAS / ("Hallazgos.xlsx" if tipo == "hallazgos" else "Evidencias.xlsx")
        if tipo == "comunicacion":
            return _base_estatica("templates_base_revisoria/4 COMUNICACION/3_COMUNICACION.xlsx") or _falta(clave)
    raise FlujoError(f"El archivo «{clave}» no existe en este tipo de auditoría.")


def _falta(clave):
    raise FlujoError(f"No se encontró la plantilla base de «{clave}» en static/templates_base_*.")


def nombre_archivo(audit: Audit, clave: str, destino: str = "") -> str:
    mod = modulo_de(audit)
    tipo = clave.split(":")[0]
    if mod == "R" and tipo in config.NOMBRES_RF:
        return config.NOMBRES_RF[tipo]
    if mod == "I" and tipo in ("hallazgos", "evidencias"):
        return {"hallazgos": "1_Hallazgos.xlsx", "evidencias": "2_Evidencias.xlsx"}[tipo]
    if mod == "I" and tipo == "borrador":
        return "5_Borrador_Informe.xlsx"
    return ruta_base(audit, clave, destino).name if tipo != "informe" or mod == "F" else (
        config.areas_ai().get(destino, {}).get("informe") or f"Informe Auditoría {nombre_destino_area(destino)}.docx")


def nombre_destino_area(clave: str) -> str:
    return config.areas_ai().get(clave, {}).get("nombre", clave)


def ultima(audit: Audit, clave: str) -> ArchivoProyecto | None:
    return ArchivoProyecto.objects.filter(audit=audit, clave=clave).order_by("-version").first()


def archivos_actuales(audit: Audit) -> list[ArchivoProyecto]:
    claves = ArchivoProyecto.objects.filter(audit=audit).order_by().values_list("clave", flat=True).distinct()
    return sorted((ultima(audit, c) for c in claves), key=lambda a: a.clave)


def _guardar(audit: Audit, clave: str, ruta_tmp: str, nombre_base: str, user, motivo: str, incluidos: list[int]) -> ArchivoProyecto:
    prev = ultima(audit, clave)
    n = (prev.version if prev else 0) + 1
    stem, ext = Path(nombre_base).stem, Path(nombre_base).suffix
    nombre = f"{stem}_v{n}{ext}"
    sha = hashlib.sha256(Path(ruta_tmp).read_bytes()).hexdigest()
    with open(ruta_tmp, "rb") as fh:
        reg = ArchivoProyecto(audit=audit, clave=clave, version=n, nombre=nombre, sha256=sha, motivo=motivo[:200],
                              hallazgos_incluidos=incluidos, creado_por=user if getattr(user, "pk", None) else None)
        reg.archivo.save(nombre, File(fh), save=False)
        reg.save()
    return reg


def _abrir_xlsx(audit: Audit, clave: str, destino: str = ""):
    """(libro, es_nuevo): la última versión del archivo o su plantilla base (primera vez)."""
    prev = ultima(audit, clave)
    if prev:
        with prev.archivo.open("rb") as fh:
            return load_workbook(fh), False
    return load_workbook(ruta_base(audit, clave, destino)), True


def _guardar_xlsx(audit, clave, wb, destino, user, motivo, incluidos):
    with tempfile.TemporaryDirectory() as tmp:
        p = str(Path(tmp) / "salida.xlsx")
        wb.save(p)
        return _guardar(audit, clave, p, nombre_archivo(audit, clave, destino), user, motivo, incluidos)


def _refs(audit: Audit, destino: str) -> tuple[str, str]:
    mod = modulo_de(audit)
    if mod == "F":
        c = config.cuentas_fin().get(destino, {})
        return c.get("rh", ""), c.get("re", "")
    if mod == "I":
        return config.REFS_AI["hallazgos"], config.REFS_AI["evidencias"]
    return config.REFS_RF["hallazgos"], config.REFS_RF["evidencias"]


def _preparar_nuevo(wb, audit: Audit, clave: str, destino: str, user) -> None:
    """Primera vez: encabezado dinámico (entidad, período, moneda, tipo, referencias) y firmas."""
    rh, re_ = _refs(audit, destino)
    ref = rh if clave.startswith("hallazgos") else re_
    xl.aplicar_encabezado(wb, audit)
    ws = wb.worksheets[0]
    # esquina de referencias: la «Ref.» de la hoja (U1 / T1) y la referencia cruzada (Q1 / P1) salen de la tabla de configuración
    celdas = ("Q1", "U1") if clave.startswith("hallazgos") else ("P1", "T1")
    for i, c in enumerate(celdas):
        if ref and ws[c].value is not None:
            ws[c].value = ref
    _firmar(wb, audit, user)


def _nombre_usuario(u) -> str:
    return (getattr(u, "get_full_name", lambda: "")() or getattr(u, "username", "") or "").strip()


def _firmar(wb, audit: Audit, user, revisor=None) -> None:
    hoy = date.today().strftime("%d/%m/%Y")
    xl.firmas(wb, elaboro=_nombre_usuario(user) or None, reviso=_nombre_usuario(revisor) if revisor else None,
              fecha_elaboro=hoy, fecha_reviso=hoy if revisor else None)


def _contexto(audit: Audit, user=None, revisor=None) -> dict:
    c = xl.contexto_proyecto(audit)
    c.update(elaboro=_nombre_usuario(user) if user else "", reviso=_nombre_usuario(revisor) if revisor else _nombre_usuario(audit.audit_manager),
             fecha=date.today().strftime("%d/%m/%Y"))
    return c


# ----------------------------------------------------------------------------- derivar hallazgo desde Audita Análisis
CLASIF_POR_AGENTE = {
    "F": {"fraudes": "Control Interno", "contratos": "Cumplimiento Normativo", "masivo": "Presentación de EEFF"},
    "I": {"fraudes": "Fraude / Irregularidades", "contratos": "Cumplimiento Legal", "masivo": "Control Interno"},
    "R": {"fraudes": "Fraude / Irregularidades", "contratos": "Cumplimiento Legal", "masivo": "Control Interno"},
}
SEV_POR_ALERTA = {"Alta": "Alta", "Media": "Media", "Baja": "Baja"}


def _titulo(ha: HallazgoAnalisis) -> str:
    t = (ha.procedimiento or "").strip().rstrip(".")
    t = re.sub(r"\s+", " ", t)
    return (t[:1].upper() + t[1:])[:200] or f"Hallazgo {ha.codigo}"


def derivar(ha: HallazgoAnalisis, modulo: str, over: dict | None = None) -> dict:
    over = over or {}
    clas = CLASIF_POR_AGENTE.get(modulo, {}).get(ha.agente, "Control Interno")
    condicion = (ha.condicion or ha.resultado or "").strip()
    return {
        "titulo": (over.get("titulo") or _titulo(ha)).strip()[:300],
        "condicion": condicion,
        "criterio": (ha.criterio or "").strip() or (f"{ha.nia}. " if ha.nia else "") + config.CRITERIO_POR_DEFECTO.get(modulo, ""),
        "causa": (ha.causa or "").strip() or "Por confirmar con la gerencia: el análisis automatizado no determina la causa.",
        "efecto": (ha.efecto or "").strip() or "Por evaluar por el auditor.",
        "recomendacion": (ha.recomendacion or "").strip() or "Por definir por el auditor.",
        "clasificacion": over.get("clasificacion") or clas,
        "severidad": over.get("severidad") or SEV_POR_ALERTA.get(ha.alerta, "Media"),
        "monto": ha.importe,
        "responsable": (over.get("responsable") or "").strip(),
    }


def huella_de(corrida_id: int, origen_id: int, destino: str, condicion: str) -> str:
    h = hashlib.sha256((condicion or "").encode("utf-8")).hexdigest()[:16]
    return hashlib.sha256(f"{corrida_id}|{origen_id}|{destino}|{h}".encode()).hexdigest()


def _evidencia_de(h: Hallazgo, ha: HallazgoAnalisis, corrida: CorridaAnalisis) -> EvidenciaHallazgo:
    docs = ", ".join(d.nombre_original for d in corrida.documentos.all()[:4])
    fuente = (ha.origen or docs or f"Análisis #{corrida.pk}")[:300]
    desc = f"{ha.procedimiento}: {(ha.resultado or '')[:500]}"
    return EvidenciaHallazgo(
        hallazgo=h, tipo="A", descripcion=desc, fuente=fuente,
        fecha_obtencion=(corrida.terminado_en or corrida.creado_en).date(),
        conclusion="Resultado del análisis automatizado; la suficiencia y pertinencia (NIA 500) las decide el auditor.",
        ref_archivo=f"Audita Análisis · análisis #{corrida.pk}" + (f" · {ha.codigo}" if ha.codigo else ""))


# ----------------------------------------------------------------------------- etapa 1-2: enviar a papel de trabajo
@transaction.atomic
def enviar_a_papel(user, corrida: CorridaAnalisis, ids: list[int], *, destino: str = "", overrides: dict | None = None,
                   plazo_dias: int | None = None) -> dict:
    """Escribe los hallazgos elegidos en las plantillas de Hallazgos y Evidencias de la cuenta o el área."""
    audit = Audit.objects.select_for_update().get(pk=corrida.audit_id)
    _acceso(user, audit)
    mod = modulo_de(audit)
    if corrida.revision == CorridaAnalisis.Revision.RECHAZADO:
        raise FlujoError("El análisis fue rechazado: no se puede enviar a papel de trabajo.")
    if mod == "F":
        if destino not in config.cuentas_fin():
            raise FlujoError("Elija la cuenta contable a la que corresponde el hallazgo.")
    elif mod == "I":
        if destino not in config.areas_ai():
            raise FlujoError("Elija el área: define a qué informe específico llega el hallazgo.")
    else:
        destino = ""
    if not ids:
        raise FlujoError("Seleccione al menos un hallazgo.")
    elegidos = list(corrida.hallazgos.filter(pk__in=ids).exclude(decision=HallazgoAnalisis.Decision.DESCARTADO).order_by("orden", "id"))
    if not elegidos:
        raise FlujoError("Los hallazgos elegidos no existen o están descartados.")
    nuevos, duplicados = [], []
    overrides = overrides or {}
    for ha in elegidos:
        datos = derivar(ha, mod, overrides.get(ha.pk))
        huella = huella_de(corrida.pk, ha.pk, destino, datos["condicion"])
        if Hallazgo.objects.filter(audit=audit, huella=huella).exists():
            duplicados.append(ha.codigo or str(ha.pk))
            continue
        if plazo_dias:
            datos["fecha_seguimiento"] = date.today() + timedelta(days=int(plazo_dias))
        h = Hallazgo.objects.create(
            audit=audit, corrida=corrida, origen=ha, modulo=mod, cuenta=destino if mod == "F" else "", area=destino if mod == "I" else "",
            huella=huella, estado=config.EN_PAPEL, creado_por=user, **datos)
        ev = _evidencia_de(h, ha, corrida)
        ev.save()
        nuevos.append((h, ev))
    colocados = []
    if nuevos:
        colocados = _colocar(audit, user, nuevos, destino)
    resumen = {"enviados": [h.pk for h, _ in nuevos], "duplicados": duplicados, "colocados": colocados}
    _log(audit, user, "enviar_a_papel", "corrida", corrida.pk, {}, {"destino": destino, "enviados": len(nuevos), "duplicados": duplicados})
    return resumen


def _colocar(audit: Audit, user, nuevos: list[tuple[Hallazgo, EvidenciaHallazgo]], destino: str) -> list[dict]:
    mod = modulo_de(audit)
    k_h, k_e = f"hallazgos:{destino or 'rf'}", f"evidencias:{destino or 'rf'}"
    wb, nuevo = _abrir_xlsx(audit, k_h, destino)
    if nuevo:
        _preparar_nuevo(wb, audit, k_h, destino, user)
    area_txt = nombre_destino(nuevos[0][0]) or ("Revisoría Fiscal" if mod == "R" else "")
    filas_h = xl.escribir_hallazgos(wb, [h for h, _ in nuevos], modulo=mod, area_nombre=area_txt)
    xl.actualizar_estado(wb, {})
    regh = _guardar_xlsx(audit, k_h, wb, destino, user, f"Se agregan {len(nuevos)} hallazgo(s) desde Audita Análisis", [h.pk for h, _ in nuevos])
    refs = {}
    for f, (h, _) in zip(filas_h, nuevos):
        h.ref_local = f.ref
        h.save(update_fields=["ref_local"])
        refs[h.pk] = f.ref
        ColocacionHallazgo.objects.create(hallazgo=h, clave=k_h, hoja=f.hoja, fila=f.fila, ref_local=f.ref)
    wb2, nuevo2 = _abrir_xlsx(audit, k_e, destino)
    if nuevo2:
        _preparar_nuevo(wb2, audit, k_e, destino, user)
    filas_e = xl.escribir_evidencias(wb2, [e for _, e in nuevos], refs)
    presentes = [h.ref_local for h in Hallazgo.objects.filter(audit=audit, modulo=mod, **({"cuenta": destino} if mod == "F" else {"area": destino} if mod == "I" else {})) if h.ref_local]
    xl.actualizar_matriz(wb2, presentes)
    _guardar_xlsx(audit, k_e, wb2, destino, user, f"Se agregan {len(nuevos)} evidencia(s)", [h.pk for h, _ in nuevos])
    for f, (h, e) in zip(filas_e, nuevos):
        e.ref_local = f.ref
        e.save(update_fields=["ref_local"])
        ColocacionHallazgo.objects.create(hallazgo=h, evidencia=e, clave=k_e, hoja=f.hoja, fila=f.fila, ref_local=f.ref)
    return [{"hallazgo": h.pk, "ref": h.ref_local, "evidencia": e.ref_local, "hoja": f.hoja, "fila": f.fila}
            for f, (h, e) in zip(filas_h, nuevos)]


# ----------------------------------------------------------------------------- la plantilla es la fuente de verdad
_CAMPOS_LEER = {"titulo": "titulo", "condicion": "condicion", "criterio": "criterio", "causa": "causa", "efecto": "efecto",
                "recom": "recomendacion", "respuesta": "respuesta_administracion", "clasif": "clasificacion",
                "respons": "responsable", "prioridad": "severidad", "signif": "significativo"}


def sincronizar_desde_plantillas(audit: Audit, user=None) -> list[dict]:
    """Lee lo que el auditor editó en las plantillas de Hallazgos y Evidencias y lo guarda en el sistema (excepto hallazgos bloqueados)."""
    cambios = []
    for clave in ColocacionHallazgo.objects.filter(hallazgo__audit=audit, clave__startswith="hallazgos:").values_list("clave", flat=True).distinct():
        arch = ultima(audit, clave)
        if not arch:
            continue
        with arch.archivo.open("rb") as fh:
            filas = xl.leer_hallazgos(load_workbook(fh))
        for col in ColocacionHallazgo.objects.filter(hallazgo__audit=audit, clave=clave, evidencia__isnull=True).select_related("hallazgo"):
            h, fila = col.hallazgo, filas.get(col.ref_local)
            if not fila or h.bloqueado:
                continue
            antes, despues = {}, {}
            for k, campo in _CAMPOS_LEER.items():
                v = fila.get(k)
                v = "" if v is None else str(v).strip()
                if campo == "severidad" and v not in config.SEVERIDADES:
                    continue
                if v != (getattr(h, campo) or "") and not (campo == "significativo" and v not in ("Sí", "No", "")):
                    antes[campo], despues[campo] = getattr(h, campo), v
                    setattr(h, campo, v)
            fs = fila.get("fecha")
            if isinstance(fs, (datetime, date)):
                fs = fs.date() if isinstance(fs, datetime) else fs
                if fs != h.fecha_seguimiento:
                    antes["fecha_seguimiento"], despues["fecha_seguimiento"] = str(h.fecha_seguimiento or ""), str(fs)
                    h.fecha_seguimiento = fs
            if despues:
                h.save()
                _log(audit, user, "edicion_en_plantilla", "hallazgo", h.finding_id, antes, despues)
                cambios.append({"hallazgo": h.pk, "ref": h.ref_local, **despues})
    for clave in ColocacionHallazgo.objects.filter(hallazgo__audit=audit, clave__startswith="evidencias:").values_list("clave", flat=True).distinct():
        arch = ultima(audit, clave)
        if not arch:
            continue
        with arch.archivo.open("rb") as fh:
            filas = xl.leer_evidencias(load_workbook(fh))
        for col in ColocacionHallazgo.objects.filter(hallazgo__audit=audit, clave=clave, evidencia__isnull=False).select_related("evidencia", "hallazgo"):
            e, fila = col.evidencia, filas.get(col.ref_local)
            if not fila or col.hallazgo.bloqueado:
                continue
            nuevo = {"descripcion": fila.get("desc"), "fuente": fila.get("fuente"), "suficiente": fila.get("sufic"),
                     "apropiada": fila.get("aprop"), "confiabilidad": fila.get("confia"), "conclusion": fila.get("obs")}
            despues = {}
            for campo, v in nuevo.items():
                v = "" if v is None else str(v).strip()
                if v != (getattr(e, campo) or ""):
                    despues[campo] = v
                    setattr(e, campo, v)
            if despues:
                e.save()
                _log(audit, user, "edicion_evidencia_en_plantilla", "evidencia", e.evidence_id, {}, despues)
                cambios.append({"evidencia": e.pk, "ref": e.ref_local, **despues})
    return cambios


# ----------------------------------------------------------------------------- estados en las plantillas
def _marcar_estado_en_plantillas(audit: Audit, user, hallazgos: list[Hallazgo], motivo: str) -> None:
    """Estado de cada hallazgo en su plantilla (+ las 4 preguntas de COMUNICACIÓN DE HALLAZGOS) en una sola versión nueva por archivo."""
    por_clave: dict[str, dict[str, str]] = {}
    for h in hallazgos:
        for col in h.colocaciones.filter(evidencia__isnull=True, clave__startswith="hallazgos:"):
            por_clave.setdefault(col.clave, {})[col.ref_local] = etiqueta_estado(h)
    for clave, estados in por_clave.items():
        destino = clave.split(":", 1)[1]
        base = "" if destino == "rf" else destino
        wb, _ = _abrir_xlsx(audit, clave, base)
        xl.actualizar_estado(wb, estados)
        xl.sombrear_bloqueados(wb, {r for r, e in estados.items() if e in ("Aprobado", "Incluido en informe", "Comunicado")})
        _marcar_comunicacion_en(wb, Hallazgo.objects.filter(audit=audit, colocaciones__clave=clave).distinct())
        _guardar_xlsx(audit, clave, wb, base, user, motivo, [h.pk for h in hallazgos])


def _marcar_comunicacion_en(wb, hs) -> None:
    """COMUNICACIÓN DE HALLAZGOS (4 preguntas Sí/No): se marca desde el sistema cuando se comunica o responde un hallazgo."""
    info = xl.preguntas_comunicacion(wb)
    if not info:
        return
    ws, filas, col = info
    comunicado = hs.filter(estado__in=[config.APROBADO, config.INCLUIDO]).exists()
    respondido = hs.exclude(respuesta_administracion="").exists()
    for fila, valor in zip(filas, (comunicado, comunicado, respondido, False)):
        xl._set(ws, fila, col, "Sí" if valor else None)


# ----------------------------------------------------------------------------- etapa 3: a revisión
def _evidencias_texto(h: Hallazgo) -> list[str]:
    return [f"{e.ref_local or 'EV'} ({config.TIPOS_EVIDENCIA.get(e.tipo, '')}): {e.descripcion[:160]} — {e.fuente} — {e.fecha_obtencion.strftime('%d/%m/%Y') if e.fecha_obtencion else ''}"
            for e in h.evidencias.all()]


def _decision_de(h: Hallazgo):
    r = h.revisiones.exclude(decision="reabrir").order_by("-id").first()
    if not r:
        return "", "", ""
    return r.get_decision_display(), r.comentario, f"{_nombre_usuario(r.revisor)} · {r.decidido_en.strftime('%d/%m/%Y')}"


@transaction.atomic
def enviar_a_revision(user, audit: Audit, ids: list[int]) -> dict:
    _acceso(user, audit)
    sincronizar_desde_plantillas(audit, user)
    hs = list(Hallazgo.objects.filter(audit=audit, pk__in=ids, estado__in=[config.EN_PAPEL, config.DEVUELTO]))
    if not hs:
        raise FlujoError("No hay hallazgos en papel de trabajo para enviar a revisión.")
    for h in hs:
        antes = h.estado
        h.estado = config.EN_REVISION
        h.save(update_fields=["estado"])
        _log(audit, user, "enviar_a_revision", "hallazgo", h.finding_id, {"estado": antes}, {"estado": h.estado})
    _marcar_estado_en_plantillas(audit, user, hs, "Pasan a revisión")
    _reconstruir_consolidado(audit, user)
    return {"enviados": [h.pk for h in hs]}


def _reconstruir_consolidado(audit: Audit, user) -> None:
    """5.5.3 (Financiera) o borrador del informe (Auditoría Interna): se regeneran desde el estado del sistema."""
    mod = modulo_de(audit)
    if mod == "R":
        return
    hs = list(Hallazgo.objects.filter(audit=audit).exclude(estado__in=[config.BORRADOR, config.EN_PAPEL]).order_by("id"))
    if not hs:
        return
    ctx = _contexto(audit, user)
    if mod == "F":
        wb = load_workbook(ruta_base(audit, "revision"))
        xl.aplicar_encabezado(wb, audit)
        xl2.llenar_revision(
            wb, hs, cuenta_nombre=nombre_destino, evidencias_de=lambda h: [e.ref_local for e in h.evidencias.all() if e.ref_local],
            ref_origen=lambda h: f"{config.cuentas_fin().get(h.cuenta, {}).get('rh', '')} / {h.ref_local}", decision_de=_decision_de, ctx=ctx)
        _guardar_xlsx(audit, "revision", wb, "", user, "Consolidado de hallazgos para revisión", [h.pk for h in hs])
    else:
        wb = load_workbook(ruta_base(audit, "borrador"))
        xl.aplicar_encabezado(wb, audit)
        info = xl2.llenar_borrador(
            wb, hs, area_texto=lambda h: f"Informe: {nombre_destino(h)} ({config.areas_ai().get(h.area, {}).get('ref', '')})",
            ctx=ctx, usuario=_nombre_usuario(user), fecha_envio=date.today())
        n = ArchivoProyecto.objects.filter(audit=audit, clave="borrador").count() + 1
        xl2.registrar_version_borrador(info["control"], info["version_fila"], numero=n,
                                       descripcion="Hallazgos desde Audita Análisis", agregados=len(hs), usuario=_nombre_usuario(user), fecha=date.today())
        xl._set(info["control"], info["version_fila"], 9, _nombre_usuario(audit.audit_manager))
        xl.firmas(wb, elaboro=_nombre_usuario(user), reviso=_nombre_usuario(audit.audit_manager))
        _guardar_xlsx(audit, "borrador", wb, "", user, "Borrador del informe: hallazgos en revisión", [h.pk for h in hs])


# ----------------------------------------------------------------------------- etapa 4: decisión del jefe
def _notificar(audit: Audit, de, h: Hallazgo, texto: str) -> None:
    """Notificación al auditor (módulo Notificaciones); si el módulo no la admite se sigue sin ella."""
    try:
        from notifications.services import create_notification

        dest = h.creado_por
        if dest and dest.pk != de.pk:
            create_notification(audit.pk, [dest.pk], de.pk, texto)
    except Exception:  # noqa: BLE001 - la notificación nunca debe frenar la decisión
        pass


@transaction.atomic
def decidir(user, hallazgo: Hallazgo, decision: str, comentario: str = "") -> Hallazgo:
    hallazgo.refresh_from_db()
    audit = hallazgo.audit
    _acceso(user, audit)
    comentario = (comentario or "").strip()
    if decision not in ("aprobar", "devolver", "rechazar"):
        raise FlujoError("Decisión no válida.")
    if hallazgo.estado != config.EN_REVISION:
        raise FlujoError("Solo se decide sobre hallazgos que están en revisión.")
    if not puede_decidir(user, audit):
        raise FlujoError("Solo el Jefe de Auditoría aprueba, devuelve o rechaza hallazgos.")
    if not es_individual(audit) and hallazgo.creado_por_id == user.pk:
        raise FlujoError("En una auditoría con equipo nadie aprueba sus propios hallazgos.")
    if decision in ("devolver", "rechazar") and not comentario:
        raise FlujoError("El comentario es obligatorio al devolver o rechazar.")
    if decision == "aprobar" and not hallazgo.evidencias.exists():
        raise FlujoError("No se aprueban hallazgos sin evidencia vinculada.")
    sincronizar_desde_plantillas(audit, user)
    hallazgo.refresh_from_db()
    destino = {"aprobar": config.APROBADO, "devolver": config.DEVUELTO, "rechazar": config.RECHAZADO}[decision]
    antes = hallazgo.estado
    hallazgo.estado = destino
    hallazgo.bloqueado = destino == config.APROBADO
    hallazgo.save(update_fields=["estado", "bloqueado"])
    individual = es_individual(audit)
    RevisionHallazgo.objects.create(hallazgo=hallazgo, revisor=user, decision=decision, comentario=comentario, auditoria_individual=individual)
    _log(audit, user, f"decision_{decision}", "hallazgo", hallazgo.finding_id, {"estado": antes}, {"estado": destino, "comentario": comentario})
    if individual:
        _log(audit, user, "auditoria_individual", "hallazgo", hallazgo.finding_id, {}, {"nota": "Auditoría individual: elaboró y aprobó el mismo usuario"})
    if decision == "devolver":
        _notificar(audit, user, hallazgo, f"Hallazgo {hallazgo.ref_local} devuelto: {comentario}")
    _marcar_estado_en_plantillas(audit, user, [hallazgo], f"Decisión del jefe: {decision}")
    _reconstruir_consolidado(audit, user)
    mod = modulo_de(audit)
    if mod == "I" and decision == "aprobar" and hallazgo.area != "transversal":
        generar_informe_area(user, audit, hallazgo.area)
    if mod == "R" and decision == "aprobar":
        generar_comunicacion(user, audit)
    return hallazgo


@transaction.atomic
def reabrir(user, hallazgo: Hallazgo, comentario: str) -> Hallazgo:
    hallazgo.refresh_from_db()
    audit = hallazgo.audit
    if not es_jefe(user, audit) and not (es_individual(audit) and user.pk in miembros(audit)):
        raise FlujoError("Solo el Jefe de Auditoría puede reabrir un hallazgo aprobado.")
    if hallazgo.estado not in (config.APROBADO, config.INCLUIDO):
        raise FlujoError("Solo se reabren hallazgos aprobados.")
    if not comentario.strip():
        raise FlujoError("Escriba el motivo de la reapertura.")
    antes = hallazgo.estado
    hallazgo.estado, hallazgo.bloqueado, hallazgo.hf_numero = config.EN_REVISION, False, None
    hallazgo.save(update_fields=["estado", "bloqueado", "hf_numero"])
    RevisionHallazgo.objects.create(hallazgo=hallazgo, revisor=user, decision="reabrir", comentario=comentario.strip(),
                                    auditoria_individual=es_individual(audit))
    _log(audit, user, "reabrir", "hallazgo", hallazgo.finding_id, {"estado": antes}, {"estado": hallazgo.estado, "comentario": comentario.strip()})
    _marcar_estado_en_plantillas(audit, user, [hallazgo], "Hallazgo reabierto")
    _reconstruir_consolidado(audit, user)
    return hallazgo


# ----------------------------------------------------------------------------- etapa 5: hallazgos finales e informe
def _orden_final(h: Hallazgo):
    return (config.ORDEN_SEVERIDAD.get(h.severidad, 9), nombre_destino(h), h.id)


@transaction.atomic
def aprobar_finales(user, audit: Audit) -> dict:
    """Financiera: numera HF-01…, escribe 5.5.4 (solo aprobados) y crea la versión nueva del informe, sección 5."""
    _acceso(user, audit)
    if modulo_de(audit) != "F":
        raise FlujoError("«Aprobar hallazgos finales» es de Auditoría Financiera.")
    if not puede_decidir(user, audit):
        raise FlujoError("Solo el Jefe de Auditoría aprueba los hallazgos finales.")
    sincronizar_desde_plantillas(audit, user)
    hs = sorted(Hallazgo.objects.filter(audit=audit, estado__in=[config.APROBADO, config.INCLUIDO]), key=_orden_final)
    for i, h in enumerate(hs, start=1):
        if h.hf_numero != i:
            h.hf_numero = i
            h.save(update_fields=["hf_numero"])
    ctx = _contexto(audit, user)
    wb = load_workbook(ruta_base(audit, "finales"))
    xl.aplicar_encabezado(wb, audit)
    xl2.llenar_finales(wb, hs, cuenta_nombre=nombre_destino, ctx=ctx)
    f = _guardar_xlsx(audit, "finales", wb, "", user, f"Hallazgos finales aprobados ({len(hs)})", [h.pk for h in hs])
    inf = generar_informe_fin(user, audit, hs)
    for h in hs:
        if h.estado != config.INCLUIDO:
            h.estado = config.INCLUIDO
            h.save(update_fields=["estado"])
    _marcar_estado_en_plantillas(audit, user, hs, "Incluido en el informe")
    _log(audit, user, "aprobar_hallazgos_finales", "informe", inf.version, {}, {"hallazgos": [h.ref_hf for h in hs], "informe": inf.nombre})
    return {"finales": f, "informe": inf, "hallazgos": len(hs)}


def generar_informe_fin(user, audit: Audit, hs: list[Hallazgo] | None = None) -> ArchivoProyecto:
    if hs is None:
        hs = sorted(Hallazgo.objects.filter(audit=audit, estado__in=[config.APROBADO, config.INCLUIDO]), key=_orden_final)
    prev = ultima(audit, "informe:fin")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base.docx"
        if prev:
            with prev.archivo.open("rb") as fh:
                base.write_bytes(fh.read())
        else:
            shutil.copy(ruta_base(audit, "informe:fin"), base)
        out = str(Path(tmp) / "salida.docx")
        try:
            docx_informe.generar_seccion5(str(base), out, hs, cuenta_nombre=nombre_destino, evidencias_de=_evidencias_texto, ctx=_contexto(audit, user))
        except docx_informe.InformeError as exc:
            raise FlujoError(str(exc)) from exc
        return _guardar(audit, "informe:fin", out, nombre_archivo(audit, "informe:fin"), user,
                        "Sección 5: hallazgos y recomendaciones" if hs else "Sección 5 sin hallazgos aprobados", [h.pk for h in hs])


@transaction.atomic
def generar_informe_area(user, audit: Audit, area: str) -> ArchivoProyecto:
    """Auditoría Interna: agrega los hallazgos aprobados al informe específico del área (5.1.x) como versión nueva."""
    if area not in config.areas_ai() or area == "transversal":
        raise FlujoError("Los hallazgos transversales no tienen informe propio: alimentan el Resumen Ejecutivo y la Opinión.")
    hs = list(Hallazgo.objects.filter(audit=audit, area=area, estado__in=[config.APROBADO, config.INCLUIDO]).order_by("id"))
    hs.sort(key=lambda h: (config.ORDEN_SEVERIDAD.get(h.severidad, 9), h.id))
    clave = f"informe:{area}"
    prev = ultima(audit, clave)
    base = ruta_base(audit, clave, area)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "base.docx"
        if prev:
            with prev.archivo.open("rb") as fh:
                src.write_bytes(fh.read())
        elif base.is_file():
            shutil.copy(base, src)
        else:
            docx_informe.documento_base_area(str(src), nombre_destino_area(area), xl.contexto_proyecto(audit))
        out = str(Path(tmp) / "salida.docx")
        aprob = max((r.decidido_en for h in hs for r in h.revisiones.filter(decision="aprobar")), default=timezone.now()).date()
        docx_informe.generar_hallazgos_area(str(src), out, hs, fecha_aprobacion=aprob, area_nombre=nombre_destino_area(area))
        reg = _guardar(audit, clave, out, nombre_archivo(audit, clave, area), user,
                       f"Hallazgos aprobados del área ({len(hs)})" if hs else "Sin hallazgos aprobados", [h.pk for h in hs])
    for h in hs:
        if h.estado != config.INCLUIDO:
            h.estado = config.INCLUIDO
            h.save(update_fields=["estado"])
    _marcar_estado_en_plantillas(audit, user, hs, "Incluido en el informe del área")
    _log(audit, user, "generar_informe_area", "informe", reg.version, {}, {"area": area, "hallazgos": len(hs), "archivo": reg.nombre})
    return reg


@transaction.atomic
def generar_comunicacion(user, audit: Audit) -> ArchivoProyecto:
    """Revisoría Fiscal: reemplaza el bloque amarillo de R-3 sección 7 por los hallazgos aprobados (versión nueva)."""
    hs = list(Hallazgo.objects.filter(audit=audit, estado__in=[config.APROBADO, config.INCLUIDO]).order_by("id"))
    hs.sort(key=lambda h: (config.ORDEN_SEVERIDAD.get(h.severidad, 9), h.id))
    prev = ultima(audit, "comunicacion")
    if prev:
        with prev.archivo.open("rb") as fh:
            wb = load_workbook(fh)
    else:
        wb = load_workbook(ruta_base(audit, "comunicacion"))
        xl.aplicar_encabezado(wb, audit)
    try:
        info = xl2.escribir_r3(wb, hs, evidencias_texto=lambda h: "Evidencias: " + (", ".join(e.ref_local for e in h.evidencias.all() if e.ref_local) or "—")
                               + f" (ver {config.NOMBRES_RF['evidencias'].rsplit('.', 1)[0]})")
    except xl2.R3Error as exc:
        raise FlujoError(str(exc)) from exc
    reg = _guardar_xlsx(audit, "comunicacion", wb, "", user, f"R-3 sección 7: {len(hs)} hallazgo(s)", [h.pk for h in hs])
    for h in hs:
        if h.estado != config.INCLUIDO:
            h.estado = config.INCLUIDO
            h.save(update_fields=["estado"])
    _marcar_estado_en_plantillas(audit, user, hs, "Comunicado en R-3")
    _log(audit, user, "generar_comunicacion", "archivo", reg.version, {}, {**info, "hallazgos": len(hs)})
    return reg


def regenerar(user, audit: Audit, area: str = "") -> ArchivoProyecto:
    """Botón «Regenerar»: vuelve a escribir sección 5, informe del área o R-3 con el estado actual."""
    _acceso(user, audit)
    if not puede_decidir(user, audit):
        raise FlujoError("Solo el Jefe de Auditoría regenera los informes.")
    sincronizar_desde_plantillas(audit, user)
    mod = modulo_de(audit)
    if mod == "F":
        return aprobar_finales(user, audit)["informe"]
    if mod == "I":
        return generar_informe_area(user, audit, area)
    return generar_comunicacion(user, audit)


# ----------------------------------------------------------------------------- consultas para la interfaz
def hallazgos_de(audit: Audit):
    return Hallazgo.objects.filter(audit=audit).select_related("creado_por").prefetch_related("evidencias", "colocaciones")


def resumen_por_estado(audit: Audit) -> dict[str, int]:
    out = {k: 0 for k in config.ETIQUETA_ESTADO}
    for h in Hallazgo.objects.filter(audit=audit).values_list("estado", flat=True):
        out[h] = out.get(h, 0) + 1
    return out
