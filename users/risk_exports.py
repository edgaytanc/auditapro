"""Exportación de matriz de riesgos con dos hojas XLSX y mapa de calor real."""
import json
import re
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from .financial_identity import financial_company

HEADERS = ("Cuenta", "Riesgo / Aserción", "Saldo", "Probabilidad", "Impacto",
           "Riesgo inherente", "Control", "Riesgo residual", "Respuesta")

def _fill(score):
    if score >= 15: return "FCA5A5"
    if score >= 10: return "FCD34D"
    if score >= 5: return "FEF08A"
    return "86EFAC"

@login_required
@require_POST
def exportar_matriz_riesgos(request):
    if len(request.body) > 1024 * 1024:
        return JsonResponse({"error": "Datos demasiado grandes"}, status=413)
    try:
        payload = json.loads(request.body)
        items = payload["riesgos"]
        if not isinstance(items, list) or len(items) > 500:
            raise ValueError("Cantidad de cuentas inválida")
        rows, counts = [], {(p, i): 0 for p in range(1, 6) for i in range(1, 6)}
        for item in items:
            p, i = int(item["prob"]), int(item["impacto"])
            if not (1 <= p <= 5 and 1 <= i <= 5): raise ValueError("Puntuación fuera de rango")
            control = str(item.get("control", "no-existe"))
            if control not in {"adecuado", "parcial", "no-existe"}: raise ValueError("Control inválido")
            factor = {"adecuado": .55, "parcial": .25, "no-existe": 0}[control]
            inherente = p * i
            residual = round(inherente * (1 - factor))
            # Evita caracteres de fórmulas de Excel en texto introducido por clientes.
            def safe(v):
                text = str(v or "")[:1500]
                return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
            rows.append((safe(item.get("cuenta")), safe(item.get("asercion")),
                float(item.get("saldo") or 0), p, i, inherente, control, residual,
                safe(item.get("respuesta"))))
            counts[p, i] += 1
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OverflowError):
        return JsonResponse({"error": "Datos de riesgo inválidos"}, status=400)
    wb = Workbook()
    ws = wb.active; ws.title = "Datos"
    company = str(payload.get("company_name") or financial_company(request)).strip()[:255]
    company = re.sub(r"[\x00-\x1f]", " ", company)
    # Protege Excel ante nombres que empiecen por un operador de fórmula.
    if company.lstrip().startswith(("=", "+", "-", "@")):
        company = "'" + company
    ws.append(["Empresa", company or "Sin especificar"])
    ws.append([])
    ws.append(HEADERS)
    for row in rows: ws.append(row)
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:I{ws.max_row}"
    for cell in ws[3]:
        cell.fill = PatternFill("solid", fgColor="1D4ED8")
        cell.font = Font(color="FFFFFF", bold=True)
    for col, width in enumerate((29, 42, 20, 16, 14, 19, 16, 19, 42), 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    for row in ws.iter_rows(min_row=4):
        row[5].fill = PatternFill("solid", fgColor=_fill(row[5].value))
        row[7].fill = PatternFill("solid", fgColor=_fill(row[7].value))
    heat = wb.create_sheet("Mapa de calor")
    heat["A1"] = "Matriz de riesgo por probabilidad e impacto"; heat["A1"].font = Font(bold=True,size=14)
    heat["A2"] = "Empresa"; heat["B2"] = company or "Sin especificar"
    heat["A3"] = "Probabilidad / Impacto"
    for impact in range(1,6): heat.cell(3, impact+1, impact)
    for rowidx,prob in enumerate(range(5,0,-1),4):
        heat.cell(rowidx,1,prob)
        for impact in range(1,6):
            c = heat.cell(rowidx, impact+1, counts[prob,impact]); c.fill=PatternFill("solid", fgColor=_fill(prob*impact)); c.alignment=Alignment(horizontal="center",vertical="center")
        heat.row_dimensions[rowidx].height=30
    heat.column_dimensions["A"].width=28
    for col in "BCDEF": heat.column_dimensions[col].width=14
    buf=BytesIO();wb.save(buf);buf.seek(0)
    response=HttpResponse(buf.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"]='attachment; filename="matriz_riesgos_y_mapa_calor.xlsx"'
    return response
