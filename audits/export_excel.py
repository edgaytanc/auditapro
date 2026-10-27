"""Exportación real de Proyectos de Auditoría. Datos recuperados del servidor."""
import json
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import Http404, JsonResponse, HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from audits.access import get_audit_for_user_or_404

HEADERS = ["ID", "Cliente", "Encargo", "Tipo", "Período", "Jefe", "Equipo", "Avance (%)", "Riesgo", "Estado", "Hallazgos"]

@login_required
@require_POST
def exportar_auditorias_excel(request):
    if len(request.body) > 20000:
        return JsonResponse({"error":"Solicitud muy grande"},status=413)
    try:
        ids = json.loads(request.body)["ids"]
        if not isinstance(ids,list) or len(ids)>500 or len(ids)!=len(set(ids)):
            raise ValueError("Lista inválida")
        ids = [int(item) for item in ids]
    except (ValueError, TypeError, KeyError, OverflowError):
        return JsonResponse({"error":"Lista inválida"},status=400)
    wb=Workbook();ws=wb.active;ws.title="Proyectos"
    ws.append(HEADERS)
    for audit_id in ids:
        try:
            audit = get_audit_for_user_or_404(request.user,audit_id, action="view",module="audits")
        except Http404:
            return JsonResponse({"error":"Una auditoría no está permitida"},status=403)
        types = {"F":"Financiera","R":"Revisoría Fiscal","I":"Interna"}
        names = (" / ".join(types.get(k,k) for k in audit.get_active_type_codes()))
        manager = audit.audit_manager.get_full_name() or audit.audit_manager.username
        team = ", ".join((u.get_full_name() or u.username) for u in audit.assigned_users.all())
        findings = audit.manual_findings_count if audit.manual_findings_count is not None else audit.findings.filter(is_active=True).count()
        def safe(val):
            val=str(val or "")[:300]
            return "'" + val if val.lstrip().startswith(("=","+","-","@")) else val
        ws.append((audit.id,safe(audit.identidad),safe(audit.title),safe(names),safe(audit.periodo_auditado),safe(manager),safe(team),audit.progress if audit.progress is not None else 0,safe(audit.get_risk_level_display()),safe(audit.get_workflow_status_display() if audit.workflow_status else ""),findings))
    ws.freeze_panes="A2"
    for col,w in {"A":10,"B":28,"C":45,"D":24,"E":24,"F":29,"G":45,"H":16,"I":18,"J":19,"K":18}.items():ws.column_dimensions[col].width=w
    if ws.max_row>1:
        table=Table(displayName="TablaProyectosAudita",ref=f"A1:K{ws.max_row}")
        table.tableStyleInfo=TableStyleInfo(name="TableStyleMedium2",showRowStripes=True,showColumnStripes=False)
        ws.add_table(table)
    else:
        for c in ws[1]:c.fill=PatternFill("solid",fgColor="1D4ED8");c.font=Font(color="FFFFFF",bold=True)
    buf=BytesIO();wb.save(buf)
    response=HttpResponse(buf.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"]='attachment; filename="proyectos_auditoria.xlsx"'
    return response
