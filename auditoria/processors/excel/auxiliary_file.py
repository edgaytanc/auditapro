def process_auxiliary_file_sheets(workbook, registros_auxiliares):
    """Procesa la hoja de registros auxiliares insertando los valores en la tabla."""
    if not workbook.worksheets: return workbook
    
    sheet = workbook.worksheets[0]
    fila_inicio, col_cuenta, col_saldo = next(((f+1, c, next((cs for cs in range(1, 10) if "SALDO" in str(sheet.cell(row=f, column=cs).value or "").upper()), 3)) 
                                             for f in range(1, 20) 
                                             for c in range(1, 10) 
                                             if "CUENTA" in str(sheet.cell(row=f, column=c).value or "").upper()), 
                                             (12, 2, 3))
    
    # Insertar registros
    for i, (cuenta, valor) in enumerate(registros_auxiliares.items()):
        if i >= 30: break
        sheet.cell(row=fila_inicio+i, column=col_cuenta).value = cuenta
        sheet.cell(row=fila_inicio+i, column=col_saldo).value = valor
        
    return workbook