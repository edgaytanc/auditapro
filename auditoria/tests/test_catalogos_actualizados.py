"""Garantiza que los catálogos de descarga correspondan a plantillas reales."""
import json
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse, resolve

CATALOGOS = {"F": ("financiera", "financiera"), "I": ("interna", "interna"), "R": ("revisoria", "revisoria")}

class DescargasPlantillasActualizadasTests(SimpleTestCase):
    def test_todos_los_archivos_del_catalogo_existen(self):
        total = 0
        for tipo, (catalogo, carpeta) in CATALOGOS.items():
            root = Path(settings.BASE_DIR) / "static" / f"templates_base_{carpeta}"
            with (Path(settings.BASE_DIR) / "auditoria" / "config" / f"folder_structure_{catalogo}.json").open(encoding="utf-8") as handle:
                tree = json.load(handle)
            def walk(node, prefix=Path()):
                for name, children in node.items():
                    if isinstance(children, dict):
                        yield from walk(children,prefix/name)
                    else:
                        yield prefix/name
            paths = list(walk(tree))
            self.assertTrue(paths, f"Catálogo {tipo} vacío")
            for path in paths:
                with self.subTest(tipo=tipo,path=str(path)):
                    self.assertTrue((root/path).is_file(),f"Falta: {root/path}")
                    # La misma vista que genera el enlace directo debe resolver por nombre.
                    url = reverse("download_document",args=(55,str(path.parent).replace("\\","/"),path.name))
                    self.assertEqual(resolve(url).url_name, "download_document")
                total += 1
        self.assertGreater(total, 100)

    def test_rutas_descargas_modal_y_patron(self):
        checks = [
            ("download_document_by_pattern",(1,"A-1")),
            ("obtener_carpetas_auditoria",(1,)),
            ("obtener_documentos_auditoria",(1,"1 PLANEACION")),
            ("descargar_documento_auditoria",(1,)),
            ("generar_documento_modal",(1,)),
            ("auditoria_detalle",(1,)),
        ]
        for name,args in checks:
            with self.subTest(name=name):
                self.assertEqual(resolve(reverse(name,args=args)).url_name,name)
