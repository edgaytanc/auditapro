/* Datos de demostración fieles al mockup entregado por el cliente. */
window.AP_PERMANENT_SEED = {
  "meta": {
    "company": "Empresa ABC S.A.",
    "period": "2024"
  },
  "sections": [
    {
      "id": "1",
      "title": "Información General",
      "tables": [
        {
          "id": "t1-1",
          "title": "Datos generales de la entidad",
          "description": "Registra los datos de identificación de la entidad y modifícalos cuando cambien.",
          "columns": [
            "Campo",
            "Dato"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "Razón Social",
                "Empresa ABC S.A."
              ],
              "guides": [
                "",
                ""
              ]
            },
            {
              "id": "r2",
              "cells": [
                "NIT",
                "123456-7"
              ],
              "guides": [
                "",
                ""
              ]
            },
            {
              "id": "r3",
              "cells": [
                "Régimen Fiscal",
                "Régimen sobre Utilidades"
              ],
              "guides": [
                "",
                "seleccionar entre Régimen sobre Utilidades, Régimen Opcional Simplificado o Pequeño Contribuyente, según conste en la constancia de inscripción de la SAT."
              ]
            },
            {
              "id": "r4",
              "cells": [
                "Dirección",
                "Zona 10, Ciudad de Guatemala"
              ],
              "guides": [
                "",
                "dirección fiscal completa, igual a como aparece en la Patente de Comercio vigente."
              ]
            },
            {
              "id": "r5",
              "cells": [
                "Representante Legal",
                "Roberto Morales"
              ],
              "guides": [
                "",
                "nombre completo según el testimonio de nombramiento vigente, no según quien firme el día de la visita."
              ]
            },
            {
              "id": "r6",
              "cells": [
                "Fecha de Constitución",
                "15/03/2018"
              ],
              "guides": [
                "",
                "fecha de la escritura pública de constitución, formato dd/mm/aaaa."
              ]
            }
          ],
          "calcIndex": -1
        }
      ]
    },
    {
      "id": "2",
      "title": "Estructura Organizacional",
      "tables": [
        {
          "id": "t2-1",
          "title": "Organigrama clave",
          "description": "Se captura una sola vez y se actualiza cuando el auditor detecta un cambio.",
          "columns": [
            "Puesto",
            "Nombre"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "Gerente General",
                "Roberto Morales"
              ],
              "guides": [
                "",
                "confirmar directamente con el cliente en la entrevista de aceptación, no asumir por el organigrama de años anteriores."
              ]
            },
            {
              "id": "r2",
              "cells": [
                "Contador General",
                "Carlos Ruiz"
              ],
              "guides": [
                "",
                "persona que firma los estados financieros del cliente, verificar con colegiado activo."
              ]
            },
            {
              "id": "r3",
              "cells": [
                "Encargado de Control Interno",
                "Cliente — a confirmar"
              ],
              "guides": [
                "",
                "si el cliente no tiene un puesto formal para esto, anotar quién realiza esa función en la práctica."
              ]
            },
            {
              "id": "r4",
              "cells": [
                "Gerente de Ventas",
                "Ana García"
              ],
              "guides": [
                "",
                "confirmar si reporta directo a Gerencia General o a otro nivel intermedio."
              ]
            }
          ],
          "calcIndex": -1
        }
      ]
    },
    {
      "id": "3",
      "title": "Leyes y Regulaciones",
      "tables": [
        {
          "id": "t3-1",
          "title": "Marco normativo aplicable",
          "description": "Registra las normas aplicables y describe cómo se aplican a la entidad.",
          "columns": [
            "Normativa",
            "Aplicación"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "Código de Comercio",
                "Constitución y operación societaria"
              ],
              "guides": [
                "",
                "mencionar el tipo de sociedad (S.A., Ltda.) y si hay algo atípico en sus estatutos."
              ]
            },
            {
              "id": "r2",
              "cells": [
                "Ley del ISR",
                "Determinación del Impuesto Sobre la Renta"
              ],
              "guides": [
                "",
                "anotar el régimen específico y la tasa aplicable a este cliente."
              ]
            },
            {
              "id": "r3",
              "cells": [
                "Ley del IVA",
                "Débito y crédito fiscal"
              ],
              "guides": [
                "",
                "anotar si el cliente es agente de retención de IVA."
              ]
            },
            {
              "id": "r4",
              "cells": [
                "NIIF para PYMES",
                "Marco contable aplicado"
              ],
              "guides": [
                "",
                "confirmar si aplica NIIF completas, NIIF PYMES, u otro marco (fiscal puro)."
              ]
            }
          ],
          "calcIndex": -1
        }
      ]
    },
    {
      "id": "4",
      "title": "Planificación de Operaciones",
      "tables": [
        {
          "id": "t4-1",
          "title": "Ciclos operativos clave",
          "description": "Registra manualmente cada ciclo operativo y su responsable.",
          "columns": [
            "Área",
            "Responsable",
            "Ciclo"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "Ventas",
                "Ana García",
                "Mensual"
              ],
              "guides": [
                "",
                "",
                "frecuencia con la que el cliente cierra y concilia este ciclo, no la frecuencia de auditoría."
              ]
            },
            {
              "id": "r2",
              "cells": [
                "Compras",
                "Carlos Ruiz",
                "Mensual"
              ],
              "guides": [
                "",
                "",
                "confirmar si hay compras recurrentes vs. compras extraordinarias que requieran otro ciclo."
              ]
            },
            {
              "id": "r3",
              "cells": [
                "Producción",
                "Luis Torres",
                "Semanal"
              ],
              "guides": [
                "",
                "",
                "aplica solo si el cliente tiene proceso productivo; si es comercializadora, marcar \"No aplica\"."
              ]
            }
          ],
          "calcIndex": -1
        }
      ]
    },
    {
      "id": "5",
      "title": "Información Administrativa",
      "tables": [
        {
          "id": "t5-1",
          "title": "Documentos legales vigentes",
          "description": "Registra los documentos y su estado después de revisarlos.",
          "columns": [
            "Documento",
            "Estado"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "Escritura de Constitución",
                "Vigente"
              ],
              "guides": [
                "",
                "verificar contra el testimonio original, no contra una copia simple."
              ]
            },
            {
              "id": "r2",
              "cells": [
                "Patente de Comercio",
                "Vigente"
              ],
              "guides": [
                "",
                "confirmar que el giro comercial inscrito coincide con la actividad real del cliente."
              ]
            },
            {
              "id": "r3",
              "cells": [
                "RTU actualizado",
                "Vigente"
              ],
              "guides": [
                "",
                "descargar del portal de la SAT el mismo día de la visita para confirmar vigencia."
              ]
            },
            {
              "id": "r4",
              "cells": [
                "Licencia Municipal",
                "Por renovar"
              ],
              "guides": [
                "",
                "marcar \"Por renovar\" si vence dentro de los próximos 90 días; \"Vencido\" si ya pasó la fecha."
              ]
            }
          ],
          "calcIndex": -1
        }
      ]
    },
    {
      "id": "6",
      "title": "Información Contable, Presupuestaria y Financiera",
      "tables": [
        {
          "id": "t6-1",
          "title": "Cuentas bancarias registradas",
          "description": "Todos los campos, incluido el saldo, se capturan a mano desde la confirmación bancaria firmada — no hay importación automática de balanza aquí.",
          "columns": [
            "Banco",
            "No. Cuenta",
            "Tipo",
            "Saldo al cierre",
            "Moneda"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "BancoGT",
                "001-234567-8",
                "Monetaria Q",
                "Q 1,245,890.50",
                "GTQ"
              ],
              "guides": [
                "nombre del banco tal como aparece en la carta de confirmación firmada por el gerente financiero del cliente.",
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r2",
              "cells": [
                "BancoGT",
                "001-234568-9",
                "Monetaria $",
                "$ 95,200.00",
                "USD"
              ],
              "guides": [
                "",
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r3",
              "cells": [
                "BancoCentral",
                "507-889900-1",
                "Ahorro Q",
                "Q 450,000.00",
                "GTQ"
              ],
              "guides": [
                "",
                "",
                "",
                "",
                ""
              ]
            }
          ],
          "calcIndex": -1
        },
        {
          "id": "t6-2",
          "title": "Estado de resultados vs. presupuesto",
          "description": "Registra los importes manualmente; la variación porcentual se calcula aquí sin consultar datos externos.",
          "columns": [
            "Indicador",
            "Real",
            "Presupuestado",
            "Variación"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "Ingresos Netos",
                "Q 10,245,600",
                "Q 12,000,000",
                "-14.6%"
              ],
              "guides": [
                "",
                "",
                "monto que el cliente entregó como presupuesto aprobado por su Junta Directiva o Gerencia, no una proyección propia del auditor.",
                ""
              ]
            },
            {
              "id": "r2",
              "cells": [
                "Costo de Ventas",
                "Q 6,890,300",
                "Q 7,500,000",
                "-8.1%"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r3",
              "cells": [
                "Utilidad Bruta",
                "Q 3,355,300",
                "Q 4,500,000",
                "-25.4%"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r4",
              "cells": [
                "Gastos Operativos",
                "Q 1,890,000",
                "Q 2,000,000",
                "-5.5%"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r5",
              "cells": [
                "Utilidad Operativa",
                "Q 1,465,300",
                "Q 2,500,000",
                "-41.4%"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r6",
              "cells": [
                "ISR Estimado",
                "Q 366,325",
                "Q 625,000",
                "-41.4%"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r7",
              "cells": [
                "Utilidad Neta",
                "Q 1,098,975",
                "Q 1,875,000",
                "-41.4%"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            }
          ],
          "calcIndex": 3
        },
        {
          "id": "t6-3",
          "title": "Ratios financieros clave",
          "description": "Registra manualmente los ratios y su evaluación según los soportes disponibles.",
          "columns": [
            "Ratio",
            "Dato",
            "Referencia",
            "Evaluación"
          ],
          "rows": [
            {
              "id": "r1",
              "cells": [
                "Liquidez Corriente",
                "2.4",
                "> 1.5",
                "Óptimo"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r2",
              "cells": [
                "Prueba Ácida",
                "1.8",
                "> 1.0",
                "Óptimo"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r3",
              "cells": [
                "Endeudamiento",
                "38%",
                "< 60%",
                "Aceptable"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            },
            {
              "id": "r4",
              "cells": [
                "Rotación CxC",
                "8.2x",
                "> 6x",
                "Eficiente"
              ],
              "guides": [
                "",
                "",
                "",
                ""
              ]
            }
          ],
          "calcIndex": -1
        }
      ]
    }
  ]
};
