from __future__ import annotations

import datetime
import hashlib
import json
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from audits.models import Audit

from .storage import document_path, get_private_storage, proyecto_path, version_path


class CorridaAnalisis(models.Model):
    """Una corrida de Audita Análisis: papel de trabajo + documentos → resultados propuestos."""

    class Estado(models.TextChoices):
        EN_COLA = "en_cola", "En cola"
        EJECUTANDO = "ejecutando", "Ejecutando"
        TERMINADO = "terminado", "Terminado"
        ERROR = "error", "Con error"
        DETENIDO = "detenido", "Detenido"

    class Revision(models.TextChoices):
        PROPUESTO = "propuesto", "Propuesto"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    ACTIVAS = (Estado.EN_COLA, Estado.EJECUTANDO)

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="corridas_analisis")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="corridas_analisis"
    )
    titulo = models.CharField(max_length=200, blank=True)
    instruccion = models.TextField(blank=True, help_text="Lo que el auditor pide, en sus palabras.")
    agentes_solicitados = models.JSONField(default=list, blank=True)
    parametros = models.JSONField(default=dict, blank=True)
    columnas = models.JSONField(default=dict, blank=True)

    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.EN_COLA, db_index=True)
    etapa = models.CharField(max_length=80, blank=True)
    progreso = models.PositiveSmallIntegerField(default=0)
    latido = models.DateTimeField(default=timezone.now)
    error_mensaje = models.TextField(blank=True)

    plan = models.JSONField(default=dict, blank=True)
    resumen = models.JSONField(default=dict, blank=True)
    tablas = models.JSONField(default=dict, blank=True)
    conclusion = models.TextField(blank=True)
    conclusion_ia = models.BooleanField(default=False)
    advertencias = models.JSONField(default=list, blank=True)
    ai_llamadas = models.PositiveIntegerField(default=0)

    revision = models.CharField(max_length=10, choices=Revision.choices, default=Revision.PROPUESTO)
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    aprobado_en = models.DateTimeField(null=True, blank=True)
    revision_comentario = models.TextField(blank=True)

    creado_en = models.DateTimeField(default=timezone.now)
    iniciado_en = models.DateTimeField(null=True, blank=True)
    terminado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Corrida de Audita Análisis"
        verbose_name_plural = "Corridas de Audita Análisis"

    def __str__(self):
        return f"#{self.pk} {self.titulo or 'Análisis'} ({self.get_estado_display()})"

    @property
    def activa(self) -> bool:
        return self.estado in self.ACTIVAS

    @property
    def plantilla(self):
        return self.documentos.filter(rol=DocumentoAnalisis.Rol.PLANTILLA).first()

    @property
    def ultima_version(self):
        return self.versiones.order_by("-numero").first()

    def touch(self, etapa: str | None = None, progreso: int | None = None) -> None:
        fields = ["latido"]
        self.latido = timezone.now()
        if etapa is not None:
            self.etapa = etapa
            fields.append("etapa")
        if progreso is not None:
            self.progreso = progreso
            fields.append("progreso")
        self.save(update_fields=fields)


class DocumentoAnalisis(models.Model):
    class Rol(models.TextChoices):
        PLANTILLA = "plantilla", "Papel de trabajo"
        AUXILIAR = "auxiliar", "Auxiliar o reporte"
        SOPORTE = "soporte", "Documento de soporte"

    corrida = models.ForeignKey(CorridaAnalisis, on_delete=models.CASCADE, related_name="documentos")
    rol = models.CharField(max_length=10, choices=Rol.choices)
    archivo = models.FileField(upload_to=document_path, storage=get_private_storage, max_length=300)
    nombre_original = models.CharField(max_length=255)
    formato = models.CharField(max_length=10)
    tamano = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    paginas_leidas = models.PositiveIntegerField(default=0)
    filas_leidas = models.PositiveIntegerField(default=0)
    estado_lectura = models.CharField(max_length=12, default="pendiente")
    nota = models.TextField(blank=True)
    subido_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.nombre_original


class HallazgoAnalisis(models.Model):
    """Riesgo, hallazgo o excepción propuesto por un agente. Nace «pendiente»."""

    class Decision(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADO = "aceptado", "Aceptado"
        DESCARTADO = "descartado", "Descartado (falso positivo)"

    corrida = models.ForeignKey(CorridaAnalisis, on_delete=models.CASCADE, related_name="hallazgos")
    orden = models.PositiveIntegerField(default=0)
    codigo = models.CharField(max_length=10, blank=True)
    agente = models.CharField(max_length=12)
    tipo = models.CharField(max_length=10)  # hallazgo | riesgo | excepcion
    procedimiento = models.CharField(max_length=300)
    resultado = models.TextField()
    importe = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    origen = models.CharField(max_length=500, blank=True)
    alerta = models.CharField(max_length=5)
    nia = models.CharField(max_length=80, blank=True)
    aseveracion = models.CharField(max_length=120, blank=True)
    condicion = models.TextField(blank=True)
    criterio = models.TextField(blank=True)
    causa = models.TextField(blank=True)
    efecto = models.TextField(blank=True)
    recomendacion = models.TextField(blank=True)
    destino_pt = models.CharField(max_length=120, blank=True)
    marcado_revision = models.BooleanField(default=False)

    decision = models.CharField(max_length=10, choices=Decision.choices, default=Decision.PENDIENTE)
    decision_nota = models.TextField(blank=True)
    decidido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    decidido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["orden"]


class CifraAnalisis(models.Model):
    """Cifra con su origen: la base de la trazabilidad por cifra y de la validación."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Sin validar"
        VERIFICADA = "verificada", "Verificada"
        CAMBIO = "cambio", "Cambió el origen"
        NO_CUADRA = "no_cuadra", "No cuadra"
        SIN_ORIGEN = "sin_origen", "No verificable"

    corrida = models.ForeignKey(CorridaAnalisis, on_delete=models.CASCADE, related_name="cifras")
    fid = models.CharField(max_length=12)
    etiqueta = models.CharField(max_length=200, blank=True)
    valor = models.DecimalField(max_digits=20, decimal_places=4)
    documento = models.ForeignKey(DocumentoAnalisis, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    documento_nombre = models.CharField(max_length=255, blank=True)
    hoja_origen = models.CharField(max_length=120, blank=True)
    pagina = models.PositiveIntegerField(null=True, blank=True)
    filas = models.JSONField(default=list, blank=True)
    agregacion = models.JSONField(null=True, blank=True)
    columna = models.IntegerField(null=True, blank=True)
    bbox = models.JSONField(null=True, blank=True)
    hoja_destino = models.CharField(max_length=120, blank=True)
    celda = models.CharField(max_length=20, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    detalle = models.CharField(max_length=300, blank=True)
    verificada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["fid"]
        constraints = [models.UniqueConstraint(fields=["corrida", "fid"], name="unica_cifra_por_corrida")]


class VersionPapel(models.Model):
    """Cada pegado en el papel de trabajo crea una versión nueva; el original no se toca."""

    corrida = models.ForeignKey(CorridaAnalisis, on_delete=models.CASCADE, related_name="versiones")
    numero = models.PositiveIntegerField()
    archivo = models.FileField(upload_to=version_path, storage=get_private_storage, max_length=300)
    nombre = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    hoja = models.CharField(max_length=120)
    celda_inicio = models.CharField(max_length=20)
    motivo = models.CharField(max_length=200, blank=True)
    informe = models.JSONField(default=dict, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    creado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-numero"]
        constraints = [models.UniqueConstraint(fields=["corrida", "numero"], name="unica_version_por_corrida")]


class BitacoraAnalisis(models.Model):
    """Bitácora encadenada (NIA 230): cada registro guarda el hash del anterior. Solo se agrega."""

    corrida = models.ForeignKey(CorridaAnalisis, on_delete=models.CASCADE, related_name="bitacora")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    accion = models.CharField(max_length=60)
    detalle = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(default=timezone.now)
    hash_anterior = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64)

    class Meta:
        ordering = ["id"]

    @staticmethod
    def _digest(prev: str, corrida_id: int, usuario_id, accion: str, detalle: dict, ts) -> str:
        payload = json.dumps(
            [prev, corrida_id, usuario_id, accion, detalle, ts.isoformat()], sort_keys=True, ensure_ascii=False, default=str
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def registrar(cls, corrida: CorridaAnalisis, usuario, accion: str, detalle: dict | None = None) -> "BitacoraAnalisis":
        detalle = detalle or {}
        last = cls.objects.filter(corrida=corrida).order_by("-id").first()
        prev = last.hash if last else ""
        now = timezone.now()
        user_id = getattr(usuario, "pk", None)
        return cls.objects.create(
            corrida=corrida, usuario=usuario if user_id else None, accion=accion, detalle=detalle, creado_en=now,
            hash_anterior=prev, hash=cls._digest(prev, corrida.pk, user_id, accion, detalle, now),
        )

    @classmethod
    def cadena_valida(cls, corrida: CorridaAnalisis) -> bool:
        prev = ""
        for rec in cls.objects.filter(corrida=corrida).order_by("id"):
            expected = cls._digest(prev, corrida.pk, rec.usuario_id, rec.accion, rec.detalle, rec.creado_en)
            if rec.hash_anterior != prev or rec.hash != expected:
                return False
            prev = rec.hash
        return True

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("La bitácora es de solo agregar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("La bitácora es de solo agregar.")


def hoy():
    return datetime.date.today()


# =============================================================================== Fase 2: flujo de hallazgos
class MapaConfig(models.Model):
    """Tabla de configuración editable: cuenta → plantillas, área → informe, referencias (guías, secciones 4 y 5)."""

    tipo = models.CharField(max_length=30, unique=True)  # cuentas_fin | areas_ai
    datos = models.JSONField(default=dict)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.tipo


class Hallazgo(models.Model):
    """Hallazgo del proyecto. ``finding_id`` no cambia nunca; H-01, HF-01 o «CRÍTICO 1» son etiquetas calculadas."""

    finding_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="hallazgos_flujo")
    corrida = models.ForeignKey(CorridaAnalisis, on_delete=models.SET_NULL, null=True, blank=True, related_name="hallazgos_flujo")
    origen = models.ForeignKey(HallazgoAnalisis, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    modulo = models.CharField(max_length=1)  # F | I | R
    cuenta = models.CharField(max_length=40, blank=True)  # clave de cuenta (Financiera)
    area = models.CharField(max_length=40, blank=True)  # clave de área (Interna)
    titulo = models.CharField(max_length=300)
    condicion = models.TextField(blank=True)
    criterio = models.TextField(blank=True)
    causa = models.TextField(blank=True)
    efecto = models.TextField(blank=True)
    recomendacion = models.TextField(blank=True)
    clasificacion = models.CharField(max_length=60, blank=True)
    severidad = models.CharField(max_length=10, default="Media")
    significativo = models.CharField(max_length=3, blank=True)
    monto = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    responsable = models.CharField(max_length=200, blank=True)
    fecha_seguimiento = models.DateField(null=True, blank=True)
    respuesta_administracion = models.TextField(blank=True)
    detalle = models.JSONField(default=dict, blank=True)  # {"head": [...], "rows": [[...]]} → tabla Word real
    estado = models.CharField(max_length=12, default="en_papel", db_index=True)
    huella = models.CharField(max_length=64)
    ref_local = models.CharField(max_length=12, blank=True)  # H-03 en su plantilla
    hf_numero = models.PositiveIntegerField(null=True, blank=True)
    bloqueado = models.BooleanField(default=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    creado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["audit", "huella"], name="hallazgo_unico_por_huella")]

    @property
    def ref_hf(self) -> str:
        return f"HF-{self.hf_numero:02d}" if self.hf_numero else ""


class EvidenciaHallazgo(models.Model):
    evidence_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    hallazgo = models.ForeignKey(Hallazgo, on_delete=models.CASCADE, related_name="evidencias")
    ref_local = models.CharField(max_length=12, blank=True)  # EV-01
    tipo = models.CharField(max_length=1, default="A")  # D T F A C O
    descripcion = models.TextField()
    fuente = models.CharField(max_length=300, blank=True)
    fecha_obtencion = models.DateField(null=True, blank=True)
    suficiente = models.CharField(max_length=10, blank=True)
    apropiada = models.CharField(max_length=10, blank=True)
    confiabilidad = models.CharField(max_length=10, blank=True)
    conclusion = models.TextField(blank=True)
    ref_archivo = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["id"]


class ArchivoProyecto(models.Model):
    """Archivo del flujo (plantilla de hallazgos, consolidado, informe…). Cada cambio crea una versión; el original no se toca."""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="archivos_flujo")
    clave = models.CharField(max_length=80)  # hallazgos:caja | evidencias:caja | revision | finales | informe:fin | informe:tesoreria | comunicacion | borrador
    version = models.PositiveIntegerField()
    archivo = models.FileField(upload_to=proyecto_path, storage=get_private_storage, max_length=300)
    nombre = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    motivo = models.CharField(max_length=200, blank=True)
    hallazgos_incluidos = models.JSONField(default=list, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    creado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["clave", "-version"]
        constraints = [models.UniqueConstraint(fields=["audit", "clave", "version"], name="version_unica_por_archivo")]


class ColocacionHallazgo(models.Model):
    """Dónde quedó cada hallazgo o evidencia dentro de una plantilla (fila y referencia local)."""

    hallazgo = models.ForeignKey(Hallazgo, on_delete=models.CASCADE, related_name="colocaciones")
    evidencia = models.ForeignKey(EvidenciaHallazgo, on_delete=models.CASCADE, null=True, blank=True, related_name="colocaciones")
    clave = models.CharField(max_length=80)  # clave de ArchivoProyecto
    hoja = models.CharField(max_length=120)
    fila = models.PositiveIntegerField()
    ref_local = models.CharField(max_length=20)

    class Meta:
        ordering = ["id"]


class RevisionHallazgo(models.Model):
    class Decision(models.TextChoices):
        APROBAR = "aprobar", "Aprobado"
        DEVOLVER = "devolver", "Devuelto"
        RECHAZAR = "rechazar", "Rechazado"
        REABRIR = "reabrir", "Reabierto"

    hallazgo = models.ForeignKey(Hallazgo, on_delete=models.CASCADE, related_name="revisiones")
    revisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    decision = models.CharField(max_length=10, choices=Decision.choices)
    comentario = models.TextField(blank=True)
    auditoria_individual = models.BooleanField(default=False)
    decidido_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]


class BitacoraProyecto(models.Model):
    """Bitácora encadenada por auditoría (usuario, fecha, antes y después). Solo se agrega."""

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="bitacora_flujo")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    accion = models.CharField(max_length=60)
    entidad = models.CharField(max_length=40, blank=True)
    entidad_id = models.CharField(max_length=60, blank=True)
    antes = models.JSONField(default=dict, blank=True)
    despues = models.JSONField(default=dict, blank=True)
    auditoria_individual = models.BooleanField(default=False)
    creado_en = models.DateTimeField(default=timezone.now)
    hash_anterior = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64)

    class Meta:
        ordering = ["id"]

    @staticmethod
    def _digest(prev, audit_id, user_id, accion, entidad, entidad_id, antes, despues, individual, ts) -> str:
        payload = json.dumps([prev, audit_id, user_id, accion, entidad, entidad_id, antes, despues, individual, ts.isoformat()],
                             sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def registrar(cls, audit, usuario, accion, entidad="", entidad_id="", antes=None, despues=None, individual=False):
        last = cls.objects.filter(audit=audit).order_by("-id").first()
        prev, now = (last.hash if last else ""), timezone.now()
        uid = getattr(usuario, "pk", None)
        antes, despues = antes or {}, despues or {}
        return cls.objects.create(
            audit=audit, usuario=usuario if uid else None, accion=accion, entidad=entidad, entidad_id=str(entidad_id),
            antes=antes, despues=despues, auditoria_individual=individual, creado_en=now, hash_anterior=prev,
            hash=cls._digest(prev, audit.pk, uid, accion, entidad, str(entidad_id), antes, despues, individual, now))

    @classmethod
    def cadena_valida(cls, audit) -> bool:
        prev = ""
        for r in cls.objects.filter(audit=audit).order_by("id"):
            exp = cls._digest(prev, audit.pk, r.usuario_id, r.accion, r.entidad, r.entidad_id, r.antes, r.despues,
                              r.auditoria_individual, r.creado_en)
            if r.hash_anterior != prev or r.hash != exp:
                return False
            prev = r.hash
        return True

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("La bitácora es de solo agregar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("La bitácora es de solo agregar.")


class ExcepcionMonitoreo(models.Model):
    """Excepción que Audita Análisis entrega a la carpeta «8 MONITOREO CONTINUO» de Auditoría Interna."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADO = "confirmado", "Confirmado"
        DESCARTADO = "descartado", "Falso positivo"
        HALLAZGO = "hallazgo", "Hallazgo registrado"

    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="excepciones_monitoreo")
    corrida = models.ForeignKey(CorridaAnalisis, on_delete=models.SET_NULL, null=True, blank=True, related_name="excepciones")
    origen = models.OneToOneField(HallazgoAnalisis, on_delete=models.SET_NULL, null=True, blank=True, related_name="excepcion")
    caso = models.CharField(max_length=30)
    tarea = models.CharField(max_length=300)
    proceso = models.CharField(max_length=60, blank=True)
    responsable = models.CharField(max_length=200, blank=True)
    riesgo = models.CharField(max_length=6, default="Medio")  # Alto | Medio | Bajo
    probabilidad = models.CharField(max_length=6, default="Media")  # Alta | Media | Baja
    fecha = models.DateField(default=hoy)
    resultado_ia = models.TextField(blank=True)
    evidencia = models.CharField(max_length=300, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    auditor_seguimiento = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    fecha_limite = models.DateField(null=True, blank=True)
    hallazgo = models.ForeignKey(Hallazgo, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    creado_en = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha", "-id"]
        constraints = [models.UniqueConstraint(fields=["audit", "caso"], name="caso_unico_por_auditoria")]
