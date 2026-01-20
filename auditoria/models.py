from django.db import models
from django.core.validators import MinValueValidator
from audits.models import Audit

# -----------------------------------------------------------------------------
# Modelo para registrar balances de cuentas
# -----------------------------------------------------------------------------
class BalanceCuentas(models.Model):
    TIPO_BALANCE_CHOICES = [
        ('ANUAL', 'Anual'),
        ('SEMESTRAL', 'Semestral'),
    ]

    SECCION_CHOICES = [
        ('Activo', 'Activo'),
        ('Pasivo', 'Pasivo'),
        ('Patrimonio', 'Patrimonio'),
    ]

    id = models.AutoField(primary_key=True)
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='balances', verbose_name='Auditoría')
    tipo_balance = models.CharField(max_length=10, choices=TIPO_BALANCE_CHOICES, verbose_name='Tipo de Balance')
    fecha_corte = models.DateField(verbose_name='Fecha de Corte')
    seccion = models.CharField(max_length=10, choices=SECCION_CHOICES, verbose_name='Sección')
    nombre_cuenta = models.CharField(max_length=100, verbose_name='Nombre de la Cuenta')
    tipo_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipo de Cuenta')
    valor = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Valor')

    class Meta:
        verbose_name = 'Balance de Cuentas'
        verbose_name_plural = 'Balances de Cuentas'
        ordering = ['audit', 'tipo_balance', 'fecha_corte', 'seccion', 'nombre_cuenta']

    def __str__(self):
        return f"{self.audit.id} - {self.tipo_balance} - {self.fecha_corte} - {self.seccion} - {self.nombre_cuenta}"

# -----------------------------------------------------------------------------
# Modelo para registrar registros auxiliares
# -----------------------------------------------------------------------------
class RegistroAuxiliar(models.Model):
    id = models.AutoField(primary_key=True)
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='registros_auxiliares', verbose_name='Auditoría')
    cuenta = models.CharField(max_length=100, verbose_name='Cuenta')
    saldo = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Saldo')

    class Meta:
        verbose_name = 'Registro Auxiliar'
        verbose_name_plural = 'Registros Auxiliares'
        ordering = ['audit', 'cuenta']

    def __str__(self):
        return f"{self.audit.id} - {self.cuenta}"

# -----------------------------------------------------------------------------
# Modelo para registrar saldos iniciales
# -----------------------------------------------------------------------------
class SaldoInicial(models.Model):
    id = models.AutoField(primary_key=True)
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name='saldos_iniciales', verbose_name='Auditoría')
    cuenta = models.CharField(max_length=100, verbose_name='Cuenta')
    saldo = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Saldo Inicial')
    fecha_corte = models.DateField(verbose_name='Fecha de Corte')

    class Meta:
        verbose_name = 'Saldo Inicial'
        verbose_name_plural = 'Saldos Iniciales'
        ordering = ['audit', 'cuenta']

    def __str__(self):
        return f"{self.audit.id} - {self.cuenta} - {self.fecha_corte}"

# -----------------------------------------------------------------------------
# Modelo para registrar ajustes y reclasificaciones (Debe / Haber)
# -----------------------------------------------------------------------------
class AjustesReclasificaciones(models.Model):
    id = models.AutoField(primary_key=True)
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name='ajustes_reclasificaciones',
        verbose_name='Auditoría',
    )
    nombre_cuenta = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Cuenta',
    )
    debe = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Debe',
        default=0,
    )
    haber = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Haber',
        default=0,
    )

    class Meta:
        verbose_name = 'Ajuste / Reclasificación'
        verbose_name_plural = 'Ajustes / Reclasificaciones'
        ordering = ['audit', 'nombre_cuenta']

    def __str__(self):
        return f"{self.audit.id} - {self.nombre_cuenta}"


# -----------------------------------------------------------------------------
# Modelo para marcas de auditoría
# -----------------------------------------------------------------------------
class AuditMark(models.Model):
    """
    Marcas de auditoría que se inyectan automáticamente en documentos descargados.
    Vinculadas a auditorías específicas y emparejadas por work_paper_number.

    Estructura actualizada (Cliente 11/2025):
    - 3 columnas principales: Símbolo, Descripción, Papel de Trabajo
    - Campo 'category' mantenido por compatibilidad pero opcional
    - Papel de Trabajo debe estar en MAYÚSCULAS para matching correcto
    - Marcas se inyectan en color ROJO
    """
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name='audit_marks',
        db_index=True,
        verbose_name='Auditoría',
        help_text='Auditoría a la que pertenece esta marca'
    )
    symbol = models.CharField(
        max_length=10,
        verbose_name='Símbolo',
        help_text='Símbolo de la marca (ej: ✓, ◊, ★)'
    )
    description = models.TextField(
        verbose_name='Descripción',
        help_text='Descripción de qué significa esta marca'
    )
    work_paper_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Papel de Trabajo',
        help_text='Código del papel de trabajo EN MAYÚSCULAS (ej: SUMARIA CAJAS Y BANCOS)'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Activo'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Actualización'
    )

    class Meta:
        db_table = 'auditoria_auditmark'
        verbose_name = 'Marca de Auditoría'
        verbose_name_plural = 'Marcas de Auditoría'
        ordering = ['work_paper_number', 'created_at']
        indexes = [
            models.Index(fields=['audit', 'is_active']),
        ]

    def __str__(self):
        wp = self.work_paper_number or 'General'
        return f"{self.symbol} - {wp} ({self.audit.title})"


class WorkPaperValidationLog(models.Model):
    """
    Registro de auditoría para validaciones de work paper numbers.
    Rastrea todas las validaciones realizadas para análisis y debugging.
    """
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name='validation_logs',
        db_index=True,
        verbose_name='Auditoría'
    )
    mark = models.ForeignKey(
        AuditMark,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='validation_logs',
        verbose_name='Marca de Auditoría'
    )
    work_paper_input = models.CharField(
        max_length=200,
        verbose_name='Work Paper Input'
    )
    validation_result = models.CharField(
        max_length=20,
        choices=[
            ('valid', 'Válido'),
            ('invalid', 'Inválido'),
            ('excluded', 'Excluido')
        ],
        verbose_name='Resultado de Validación'
    )
    matched_file = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Archivo Coincidente'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Mensaje de Error'
    )
    suggestions_json = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Sugerencias (JSON)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Validación'
    )

    class Meta:
        db_table = 'auditoria_workpapervalidationlog'
        verbose_name = 'Log de Validación'
        verbose_name_plural = 'Logs de Validación'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['audit', '-created_at']),
            models.Index(fields=['validation_result']),
        ]

    def __str__(self):
        return f"{self.work_paper_input} - {self.validation_result} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


# -----------------------------------------------------------------------------
# Modelos para el Creador de Plantillas Excel Dinámico
# -----------------------------------------------------------------------------
class SymbolLibrary(models.Model):
    """
    Biblioteca de símbolos de auditoría disponibles para plantillas.
    Incluye símbolos del sistema (30+ predeterminados) y símbolos personalizados.
    """
    CATEGORY_CHOICES = [
        ('verification', 'Verificación'),
        ('calculation', 'Cálculo'),
        ('documentation', 'Documentación'),
        ('review', 'Revisión'),
        ('analysis', 'Análisis'),
        ('custom', 'Personalizado'),
    ]

    symbol = models.CharField(
        max_length=10,
        verbose_name='Símbolo'
    )
    description = models.TextField(
        verbose_name='Descripción'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='custom',
        db_index=True,
        verbose_name='Categoría'
    )
    is_system = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Símbolo del Sistema'
    )
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name='custom_symbols',
        blank=True,
        null=True,
        verbose_name='Auditoría (para símbolos personalizados)'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Activo'
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Orden de Visualización'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )

    class Meta:
        db_table = 'auditoria_symbollibrary'
        verbose_name = 'Símbolo de Auditoría'
        verbose_name_plural = 'Biblioteca de Símbolos'
        ordering = ['category', 'display_order', 'symbol']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_system', 'is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['symbol', 'audit'],
                name='unique_symbol_per_audit',
                condition=models.Q(audit__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['symbol'],
                name='unique_system_symbol',
                condition=models.Q(is_system=True)
            ),
        ]

    def __str__(self):
        audit_suffix = f" ({self.audit.title})" if self.audit else ""
        return f"{self.symbol} - {self.description[:50]}{audit_suffix}"


class TemplateConfiguration(models.Model):
    """
    Configuración guardada de una plantilla Excel generada.
    Permite reutilizar configuraciones y mantener historial.
    """
    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name='template_configurations',
        db_index=True,
        verbose_name='Auditoría'
    )
    workbook_name = models.CharField(
        max_length=200,
        verbose_name='Nombre del Libro de Trabajo'
    )
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates',
        verbose_name='Creado Por'
    )
    configuration_json = models.JSONField(
        verbose_name='Configuración Completa (JSON)'
    )
    is_favorite = models.BooleanField(
        default=False,
        verbose_name='Favorito'
    )
    download_count = models.IntegerField(
        default=0,
        verbose_name='Veces Descargado'
    )
    last_downloaded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Última Descarga'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Actualización'
    )

    class Meta:
        db_table = 'auditoria_templateconfiguration'
        verbose_name = 'Configuración de Plantilla'
        verbose_name_plural = 'Configuraciones de Plantillas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['audit', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['is_favorite', '-created_at']),
        ]

    def __str__(self):
        return f"{self.workbook_name} - {self.audit.title} ({self.created_at.strftime('%Y-%m-%d')})"


class TemplateColumn(models.Model):
    """
    Definición de columna para una plantilla Excel.
    Especifica nombre, orden, ancho y tipo de datos.
    """
    DATA_TYPE_CHOICES = [
        ('text', 'Texto'),
        ('number', 'Número'),
        ('date', 'Fecha'),
        ('currency', 'Moneda'),
        ('percentage', 'Porcentaje'),
    ]

    template_config = models.ForeignKey(
        TemplateConfiguration,
        on_delete=models.CASCADE,
        related_name='columns',
        verbose_name='Configuración de Plantilla'
    )
    column_name = models.CharField(
        max_length=100,
        verbose_name='Nombre de Columna'
    )
    column_order = models.IntegerField(
        verbose_name='Orden de Columna'
    )
    column_width = models.IntegerField(
        default=15,
        verbose_name='Ancho de Columna'
    )
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='text',
        verbose_name='Tipo de Datos'
    )
    is_required = models.BooleanField(
        default=False,
        verbose_name='Campo Obligatorio'
    )

    class Meta:
        db_table = 'auditoria_templatecolumn'
        verbose_name = 'Columna de Plantilla'
        verbose_name_plural = 'Columnas de Plantillas'
        ordering = ['template_config', 'column_order']
        constraints = [
            models.UniqueConstraint(
                fields=['template_config', 'column_order'],
                name='unique_column_order_per_template'
            ),
        ]

    def __str__(self):
        return f"{self.column_name} (Orden: {self.column_order})"


class TemplateSymbol(models.Model):
    """
    Tabla de unión entre configuraciones de plantilla y símbolos seleccionados.
    Rastrea qué símbolos se incluyeron en cada plantilla generada.
    """
    template_config = models.ForeignKey(
        TemplateConfiguration,
        on_delete=models.CASCADE,
        related_name='selected_symbols',
        verbose_name='Configuración de Plantilla'
    )
    symbol = models.ForeignKey(
        SymbolLibrary,
        on_delete=models.CASCADE,
        related_name='template_usages',
        verbose_name='Símbolo'
    )
    display_order = models.IntegerField(
        default=0,
        verbose_name='Orden de Visualización'
    )

    class Meta:
        db_table = 'auditoria_templatesymbol'
        verbose_name = 'Símbolo de Plantilla'
        verbose_name_plural = 'Símbolos de Plantillas'
        ordering = ['template_config', 'display_order']
        constraints = [
            models.UniqueConstraint(
                fields=['template_config', 'symbol'],
                name='unique_symbol_per_template'
            ),
        ]

    def __str__(self):
        return f"{self.symbol.symbol} en {self.template_config.workbook_name}"
from django.db import models
from audits.models import Audit

class RevisoriaSubcuentaQuerySet(models.QuerySet):
    def for_cuenta(self, audit, seccion, cuenta_principal):
        """
        Devuelve las subcuentas para una cuenta principal dada,
        excluyendo filas de plantilla como 'xxxx'.
        """
        return (
            self.filter(
                audit=audit,
                seccion=seccion,
                cuenta_principal__iexact=cuenta_principal,
            )
            .exclude(nombre_subcuenta__iexact="xxxx")
            .order_by("nombre_subcuenta")
        )

class RevisoriaSubcuenta(models.Model):
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE)
    seccion = models.CharField(max_length=50)
    cuenta_principal = models.CharField(max_length=255)
    nombre_subcuenta = models.CharField(max_length=255)

    saldo_ini_anterior = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    saldo_julio_anterior = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    saldo_dic_anterior = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    ajuste_debe = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    ajuste_haber = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    saldo_dic_actual = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    es_otras_cuentas = models.BooleanField(default=False)

    # 👉 aquí usamos el QuerySet personalizado
    objects = RevisoriaSubcuentaQuerySet.as_manager()

    def __str__(self):
        return f"{self.seccion} - {self.cuenta_principal} - {self.nombre_subcuenta}"
