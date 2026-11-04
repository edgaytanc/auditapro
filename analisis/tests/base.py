from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from analisis import jobs, services
from analisis.models import CorridaAnalisis
from audits.models import Audit
from users.models import Roles, User

from . import fixtures


class AnalisisCase(TestCase):
    """Entorno aislado: carpeta temporal, ejecución en línea y sin IA."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="analisis_test_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        override = override_settings(
            ANALISIS_STORAGE_ROOT=Path(self.tmp), ANALISIS_RUN_INLINE=True, ANTHROPIC_API_KEY="", ANALISIS_USE_AI=True,
        )
        override.enable()
        self.addCleanup(override.disable)

        self.role_manager, _ = Roles.objects.get_or_create(name="audit_manager", defaults={"verbose_name": "Jefe de auditoría"})
        self.role_auditor, _ = Roles.objects.get_or_create(name="auditor", defaults={"verbose_name": "Auditor"})
        self.manager = self._user("jefe", self.role_manager)
        self.auditor = self._user("auditor1", self.role_auditor)
        self.outsider = self._user("otro_jefe", self.role_manager)
        self.audit = Audit.objects.create(title="Auditoría 2025", identidad="Distribuidora Andina", audit_manager=self.manager)
        self.audit.assigned_users.add(self.auditor)

    def _user(self, name: str, role) -> User:
        return User.objects.create_user(
            username=name, email=f"{name}@example.com", password="x-Test-12345", first_name=name, last_name="Prueba", role=role,
        )

    # -- helpers
    @staticmethod
    def upload(name: str, content: bytes) -> SimpleUploadedFile:
        return SimpleUploadedFile(name, content)

    def start(self, *, user=None, plantilla=None, auxiliares=(), soportes=(), agentes=(), parametros=None, instruccion="",
              columnas=None, titulo="Prueba") -> CorridaAnalisis:
        user = user or self.manager
        run = services.create_run(
            user, self.audit, titulo=titulo, instruccion=instruccion, agentes=list(agentes), parametros=parametros or {},
            plantilla=plantilla, auxiliares=list(auxiliares), soportes=list(soportes),
        )
        if columnas:
            run.columnas = columnas
            run.save(update_fields=["columnas"])
        jobs.submit(run.pk)
        run.refresh_from_db()
        return run

    def sample_run(self, **kw) -> CorridaAnalisis:
        """El ejemplo del mockup: auxiliar Excel + facturas PDF + contrato Word."""
        return self.start(
            auxiliares=[self.upload("Auxiliar_proveedores_2025.xlsx", fixtures.auxiliar_xlsx())],
            soportes=[
                self.upload("Facturas_noviembre.pdf", fixtures.facturas_pdf()),
                self.upload("Contrato_Asesorias_Quetzal.docx", fixtures.contrato_docx()),
            ],
            **kw,
        )

    @staticmethod
    def table(run: CorridaAnalisis, key_prefix: str) -> dict:
        for key, t in run.tablas["tablas"].items():
            if key == key_prefix or key.startswith(key_prefix):
                return t
        raise AssertionError(f"No hay tabla {key_prefix}: {list(run.tablas['tablas'])}")

    @staticmethod
    def text_of(cell) -> str:
        if isinstance(cell, dict):
            if "$d" in cell:
                return cell["$d"]
            if "$date" in cell:
                return cell["$date"]
            if "$fig" in cell:
                return AnalisisCase.text_of(cell["$fig"]["value"])
        return "" if cell is None else str(cell)
