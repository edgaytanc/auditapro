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