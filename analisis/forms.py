from __future__ import annotations

from django import forms

from .engine.agents.common import AGENTES
from .engine.normalize import parse_amount, parse_date
from .engine.template_fill import PasteOptions
from .services import accessible_audits


class NuevoAnalisisForm(forms.Form):
    """Campos de texto de un análisis nuevo. Los archivos se leen aparte en la vista."""

    audit = forms.ModelChoiceField(queryset=None, label="Proyecto de auditoría", empty_label="Seleccione…")
    titulo = forms.CharField(max_length=200, required=False, label="Nombre del análisis")
    instruccion = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}), max_length=2000, label="¿Qué necesita revisar?"
    )
    agentes = forms.MultipleChoiceField(
        required=False, choices=[(k, v) for k, v in AGENTES.items()], widget=forms.CheckboxSelectMultiple,
        label="Agentes (déjelos vacíos para que el orquestador decida)",
    )
    fecha_cierre = forms.CharField(required=False, max_length=20, label="Fecha de cierre")
    saldo_mayor = forms.CharField(required=False, max_length=30, label="Saldo según mayor")
    limite_autorizacion = forms.CharField(required=False, max_length=30, label="Límite de autorización")
    umbral_concentracion = forms.CharField(required=False, max_length=10, label="Umbral de concentración (%)")
    rango = forms.CharField(required=False, max_length=10, label="Rango aceptable (±%)")
    meses_proyectar = forms.CharField(required=False, max_length=3, label="Meses a proyectar")
    tolerancia = forms.CharField(required=False, max_length=10, label="Tolerancia del cruce (%)")
    col_grupo = forms.CharField(required=False, max_length=100, label="Columna para agrupar")
    col_importe = forms.CharField(required=False, max_length=100, label="Columna del importe")
    col_documento = forms.CharField(required=False, max_length=100, label="Columna del n.º de documento")
    col_fecha = forms.CharField(required=False, max_length=100, label="Columna de la fecha")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["audit"].queryset = accessible_audits(user).order_by("title")
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"

    def _number(self, name: str, minimum=None, maximum=None):
        raw = self.cleaned_data.get(name, "").strip()
        if not raw:
            return ""
        value = parse_amount(raw)
        if value is None:
            raise forms.ValidationError("Escriba un número válido.")
        if minimum is not None and value < minimum or maximum is not None and value > maximum:
            raise forms.ValidationError("Valor fuera de rango.")
        return str(value)

    def clean_fecha_cierre(self):
        raw = self.cleaned_data["fecha_cierre"].strip()
        if not raw:
            return ""
        parsed = parse_date(raw)
        if parsed is None:
            raise forms.ValidationError("Use el formato dd/mm/aaaa.")
        return parsed.isoformat()

    def clean_saldo_mayor(self):
        return self._number("saldo_mayor")

    def clean_limite_autorizacion(self):
        return self._number("limite_autorizacion", minimum=0)

    def clean_umbral_concentracion(self):
        return self._number("umbral_concentracion", minimum=1, maximum=100)

    def clean_rango(self):
        return self._number("rango", minimum=1, maximum=500)

    def clean_meses_proyectar(self):
        return self._number("meses_proyectar", minimum=1, maximum=24)

    def clean_tolerancia(self):
        return self._number("tolerancia", minimum=0, maximum=20)

    def parametros(self) -> dict:
        keys = ("fecha_cierre", "saldo_mayor", "limite_autorizacion", "umbral_concentracion", "rango", "meses_proyectar", "tolerancia")
        return {k: self.cleaned_data[k] for k in keys if self.cleaned_data.get(k)}

    def columnas(self) -> dict:
        mapping = {"group": "col_grupo", "amount": "col_importe", "doc": "col_documento", "date": "col_fecha"}
        return {k: self.cleaned_data[v].strip() for k, v in mapping.items() if self.cleaned_data.get(v, "").strip()}


class PegarForm(forms.Form):
    hoja = forms.CharField(required=False, max_length=120)
    celda = forms.CharField(required=False, max_length=12)
    conflicto = forms.ChoiceField(
        choices=[("siguiente_libre", "Usar la siguiente celda libre"), ("cancelar", "Cancelar"), ("sobrescribir", "Sobrescribir texto y números (nunca fórmulas)")],
        initial="siguiente_libre",
    )
    conclusion = forms.BooleanField(required=False, initial=True)
    evidencia = forms.BooleanField(required=False, initial=True)

    def options(self) -> PasteOptions:
        d = self.cleaned_data
        return PasteOptions(
            sheet=d["hoja"] or None, start=d["celda"].strip() or None, conflict=d["conflicto"],
            include_conclusion=d["conclusion"], include_evidence=d["evidencia"],
        )


class DecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=[("aceptado", "Aceptado"), ("descartado", "Descartado")])
    nota = forms.CharField(required=False, max_length=1000)


class ComentarioForm(forms.Form):
    comentario = forms.CharField(required=False, max_length=1000)
