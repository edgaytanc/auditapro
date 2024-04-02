from django.db import models
from django.conf import settings

# class Contacto(models.Model):
#     nombre = models.CharField(max_length=100, verbose_name='Nombre Contacto')
#     movil = models.CharField(max_length=15, verbose_name='Movil Contacto')
#     telefono = models.CharField(max_length=15, null=True, blank=True, verbose_name='Teléfono Contacto')
#     email = models.EmailField(verbose_name='Email Contacto')
#     cargo = models.CharField(max_length=100, null=True, blank=True, verbose_name='Cargo Contacto')
#     empresa = models.CharField(max_length=100, null=True, blank=True, verbose_name='Empresa en que labora')

#     def __str__(self):
#         return self.nombre

class Entidad(models.Model):
    nombre = models.CharField(max_length=100, null=False, blank=False, verbose_name='Nombre de Entidad')
    # direccion = models.CharField(max_length=150, null=False, blank=False, verbose_name='Direccion')
    # ciudad = models.CharField(max_length=100, null=False, blank=False, verbose_name='Ciudad')
    # pais = models.CharField(max_length=100, null=False, blank=False, verbose_name='Pais')
    # nit = models.CharField(max_length=10, null=False, blank=False, verbose_name='Nit')
    # seguroSocial = models.CharField(max_length=15, null=True, blank=True, verbose_name='Seguro Social')
    # representante = models.CharField(max_length=100, null=False, blank=False, verbose_name='Representante')
    # contacto = models.ForeignKey(Contacto,on_delete=models.CASCADE, null=False,blank=False)
    # email = models.EmailField(max_length=250, null=True, blank=True, verbose_name='Correo Electrónico')
    # telefono = models.CharField(max_length=15, null=True, blank=True, verbose_name='Teléfono')
    # whatsapp = models.CharField(max_length=15, null=True, blank=True, verbose_name='WhatsApp/Telegram')
    # sitio = models.CharField(max_length=50, null=True, blank=True, verbose_name='Sitio Web')
    # actividadE = models.CharField(max_length=100, null=True, blank=True, verbose_name='Actividad Económica')
    # actividadS = models.CharField(max_length=100, null=True, blank=True, verbose_name='Actividad de Servicios')
    # norma = models.CharField(max_length=100, null=True, blank=True, verbose_name='Norma Contable')
    creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='entidades_creadas')
    supervisores = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='entidades_supervisadas')
    auditores = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='entidades_auditadas')


    def __str__(self):
        return self.nombre
