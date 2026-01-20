/**
 * Template Creator - JavaScript for Dynamic Excel Template Creator Modal
 *
 * FEATURES:
 * - 4-step wizard navigation
 * - Real-time workbook name validation (500ms debounce)
 * - Dynamic column configuration
 * - Symbol selection with category filtering
 * - Configuration validation before download
 * - AJAX template generation and download
 *
 * SAFETY:
 * - Only creates NEW files, never modifies existing templates
 * - All validation happens client-side and server-side
 * - User feedback at every step
 */

class TemplateCreator {
    constructor(auditId) {
        this.auditId = auditId;
        this.currentStep = 1;
        this.totalSteps = 4;
        this.config = {
            workbook_name: '',
            columns: [],
            symbols: [],
            options: {
                include_headers: true,
                include_instructions: true,
                color_code_symbols: true,
                add_data_validation: false
            }
        };
        this.symbolsLibrary = [];
        this.validationTimeout = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSymbolsLibrary();
        this.addDefaultColumns();
    }

    setupEventListeners() {
        // Workbook name validation (real-time with debounce)
        $('#workbookName').on('input', () => {
            this.debounceValidation();
        });

        // Wizard navigation
        $('#nextStepBtn').on('click', () => this.nextStep());
        $('#prevStepBtn').on('click', () => this.prevStep());

        // Column management
        $('#addColumnBtn').on('click', () => this.addColumn());
        $(document).on('click', '.remove-column-btn', (e) => {
            this.removeColumn($(e.currentTarget).data('index'));
        });

        // Symbol selection
        $(document).on('click', '.symbol-card', (e) => {
            this.toggleSymbol($(e.currentTarget));
        });
        $('#selectAllSymbols').on('click', () => this.selectAllSymbols());
        $('#deselectAllSymbols').on('click', () => this.deselectAllSymbols());
        $('#symbolSearch').on('input', (e) => this.searchSymbols(e.target.value));

        // Download
        $('#downloadTemplateBtn').on('click', () => this.downloadTemplate());

        // Modal events
        $('#templateCreatorModal').on('shown.bs.modal', () => {
            this.resetWizard();
        });
    }

    // ══════════════════════════════════════════════════════════════════════════
    // STEP 1: Workbook Name Validation
    // ══════════════════════════════════════════════════════════════════════════

    debounceValidation() {
        clearTimeout(this.validationTimeout);
        this.validationTimeout = setTimeout(() => {
            this.validateWorkbookName();
        }, 500); // 500ms debounce
    }

    async validateWorkbookName() {
        const workbookName = $('#workbookName').val().trim();

        if (!workbookName) {
            this.showValidationFeedback('', false);
            return;
        }

        try {
            const response = await $.ajax({
                url: '/auditoria/api/validate-workbook-name/',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    audit_id: this.auditId,
                    workbook_name: workbookName
                })
            });

            this.showValidationFeedback(response.message, response.is_valid, response.suggestions);
            this.config.workbook_name = workbookName;

        } catch (error) {
            this.showValidationFeedback('Error al validar el nombre', false);
        }
    }

    showValidationFeedback(message, isValid, suggestions = []) {
        const $feedback = $('#workbookNameFeedback');
        const $input = $('#workbookName');
        const $suggestions = $('#workbookNameSuggestions');

        if (!message) {
            $feedback.hide();
            $input.removeClass('is-valid is-invalid');
            $suggestions.hide();
            return;
        }

        // Update input border
        $input.removeClass('is-valid is-invalid');
        if (isValid) {
            $input.addClass('is-valid');
            $feedback.removeClass('invalid').addClass('valid');
            $feedback.html(`<i class="bi bi-check-circle me-2"></i>${message}`);
        } else {
            $input.addClass('is-invalid');
            $feedback.removeClass('valid').addClass('invalid');
            $feedback.html(`<i class="bi bi-x-circle me-2"></i>${message}`);
        }

        $feedback.show();

        // Show suggestions if available
        if (suggestions && suggestions.length > 0) {
            let suggestionsHtml = '<strong>Sugerencias:</strong><br>';
            suggestions.forEach(suggestion => {
                suggestionsHtml += `<div class="suggestion-item" data-suggestion="${suggestion}">${suggestion}</div>`;
            });
            $suggestions.html(suggestionsHtml).show();

            // Handle suggestion clicks
            $('.suggestion-item').on('click', function() {
                $('#workbookName').val($(this).data('suggestion')).trigger('input');
            });
        } else {
            $suggestions.hide();
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    // STEP 2: Column Configuration
    // ══════════════════════════════════════════════════════════════════════════

    addDefaultColumns() {
        this.addColumn('Símbolo', 10, 'text', true);
        this.addColumn('Descripción', 50, 'text', true);
    }

    addColumn(name = '', width = 15, dataType = 'text', isRequired = false) {
        const index = this.config.columns.length;
        const column = {
            name: name,
            width: width,
            data_type: dataType,
            is_required: isRequired,
            order: index
        };

        this.config.columns.push(column);
        this.renderColumn(column, index);
    }

    renderColumn(column, index) {
        const columnHtml = `
            <div class="column-item" data-index="${index}">
                <div class="row align-items-center">
                    <div class="col-1 text-center">
                        <i class="bi bi-grip-vertical drag-handle"></i>
                    </div>
                    <div class="col-5">
                        <input type="text" class="form-control form-control-sm column-name"
                               value="${column.name}" placeholder="Nombre de columna"
                               data-index="${index}">
                    </div>
                    <div class="col-2">
                        <input type="number" class="form-control form-control-sm column-width"
                               value="${column.width}" min="5" max="100"
                               data-index="${index}">
                        <small class="text-muted">Ancho</small>
                    </div>
                    <div class="col-2">
                        <select class="form-select form-select-sm column-datatype" data-index="${index}">
                            <option value="text" ${column.data_type === 'text' ? 'selected' : ''}>Texto</option>
                            <option value="number" ${column.data_type === 'number' ? 'selected' : ''}>Número</option>
                            <option value="date" ${column.data_type === 'date' ? 'selected' : ''}>Fecha</option>
                            <option value="currency" ${column.data_type === 'currency' ? 'selected' : ''}>Moneda</option>
                            <option value="percentage" ${column.data_type === 'percentage' ? 'selected' : ''}>Porcentaje</option>
                        </select>
                    </div>
                    <div class="col-1">
                        <input type="checkbox" class="form-check-input column-required"
                               ${column.is_required ? 'checked' : ''} data-index="${index}">
                        <small class="text-muted">Req.</small>
                    </div>
                    <div class="col-1">
                        <button type="button" class="btn btn-sm btn-danger remove-column-btn"
                                data-index="${index}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        $('#columnsContainer').append(columnHtml);

        // Attach change events
        $(`.column-name[data-index="${index}"]`).on('change', (e) => {
            this.config.columns[index].name = e.target.value;
        });
        $(`.column-width[data-index="${index}"]`).on('change', (e) => {
            this.config.columns[index].width = parseInt(e.target.value);
        });
        $(`.column-datatype[data-index="${index}"]`).on('change', (e) => {
            this.config.columns[index].data_type = e.target.value;
        });
        $(`.column-required[data-index="${index}"]`).on('change', (e) => {
            this.config.columns[index].is_required = e.target.checked;
        });
    }

    removeColumn(index) {
        if (this.config.columns.length <= 2) {
            alert('Se requieren al menos 2 columnas');
            return;
        }

        this.config.columns.splice(index, 1);
        this.rerenderColumns();
    }

    rerenderColumns() {
        $('#columnsContainer').empty();
        this.config.columns.forEach((column, index) => {
            column.order = index;
            this.renderColumn(column, index);
        });
    }

    // ══════════════════════════════════════════════════════════════════════════
    // STEP 3: Symbol Selection
    // ══════════════════════════════════════════════════════════════════════════

    async loadSymbolsLibrary() {
        try {
            const response = await $.ajax({
                url: '/auditoria/api/symbols/library/',
                method: 'GET',
                data: {
                    audit_id: this.auditId,
                    include_custom: true
                }
            });

            this.symbolsLibrary = response.symbols;
            this.renderSymbols();
            this.updateCategoryCounts(response.categories);

        } catch (error) {
            alert('Error al cargar la biblioteca de símbolos');
        }
    }

    renderSymbols() {
        const $grid = $('#symbolGridAll');
        $grid.empty();

        this.symbolsLibrary.forEach(symbol => {
            const symbolHtml = `
                <div class="symbol-card" data-symbol-id="${symbol.id}" data-category="${symbol.category}">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="symbol-${symbol.id}">
                        <label class="form-check-label" for="symbol-${symbol.id}">
                            <div class="symbol-icon">${symbol.symbol}</div>
                            <div class="symbol-description">${symbol.description}</div>
                            <div class="badge bg-secondary mt-1">${symbol.category}</div>
                        </label>
                    </div>
                </div>
            `;
            $grid.append(symbolHtml);
        });
    }

    updateCategoryCounts(categories) {
        Object.keys(categories).forEach(category => {
            $(`span[data-category="${category}"]`).text(categories[category].count);
        });
    }

    toggleSymbol($card) {
        const symbolId = $card.data('symbol-id');
        const $checkbox = $card.find('input[type="checkbox"]');

        $checkbox.prop('checked', !$checkbox.prop('checked'));
        $card.toggleClass('selected');

        this.updateSelectedSymbols();
    }

    updateSelectedSymbols() {
        this.config.symbols = [];

        $('.symbol-card.selected').each((index, element) => {
            const symbolId = $(element).data('symbol-id');
            const symbol = this.symbolsLibrary.find(s => s.id === symbolId);

            if (symbol) {
                this.config.symbols.push({
                    symbol: symbol.symbol,
                    description: symbol.description,
                    category: symbol.category
                });
            }
        });

        this.updateSymbolCounter();
    }

    updateSymbolCounter() {
        const count = this.config.symbols.length;
        const minRequired = 30;
        const percentage = Math.min((count / minRequired) * 100, 100);

        $('#symbolCount').text(`${count} / ${minRequired}`);
        $('#symbolProgress').css('width', `${percentage}%`);

        if (count >= minRequired) {
            $('#symbolCount').removeClass('bg-primary').addClass('bg-success');
        } else {
            $('#symbolCount').removeClass('bg-success').addClass('bg-primary');
        }
    }

    selectAllSymbols() {
        $('.symbol-card').addClass('selected').find('input[type="checkbox"]').prop('checked', true);
        this.updateSelectedSymbols();
    }

    deselectAllSymbols() {
        $('.symbol-card').removeClass('selected').find('input[type="checkbox"]').prop('checked', false);
        this.updateSelectedSymbols();
    }

    searchSymbols(query) {
        const lowerQuery = query.toLowerCase();

        $('.symbol-card').each(function() {
            const $card = $(this);
            const description = $card.find('.symbol-description').text().toLowerCase();
            const symbol = $card.find('.symbol-icon').text().toLowerCase();

            if (description.includes(lowerQuery) || symbol.includes(lowerQuery)) {
                $card.show();
            } else {
                $card.hide();
            }
        });
    }

    // ══════════════════════════════════════════════════════════════════════════
    // STEP 4: Preview & Download
    // ══════════════════════════════════════════════════════════════════════════

    updatePreviewSummary() {
        $('#summaryWorkbookName').text(this.config.workbook_name);
        $('#summaryColumnCount').text(this.config.columns.length);
        $('#summarySymbolCount').text(this.config.symbols.length);

        const isValid = this.config.symbols.length >= 30 && this.config.columns.length >= 2;
        const statusHtml = isValid
            ? '<span class="badge bg-success">Válido</span>'
            : '<span class="badge bg-danger">Incompleto</span>';
        $('#summaryValidationStatus').html(statusHtml);
    }

    async downloadTemplate() {
        // Collect options
        this.config.options.include_headers = $('#optionIncludeHeaders').is(':checked');
        this.config.options.include_instructions = $('#optionIncludeInstructions').is(':checked');
        this.config.options.color_code_symbols = $('#optionColorCodeSymbols').is(':checked');
        const saveConfig = $('#optionSaveConfig').is(':checked');

        // Show progress
        $('#downloadTemplateBtn').prop('disabled', true);
        $('#downloadProgress').show();

        try {
            const payload = {
                audit_id: this.auditId,
                workbook_name: this.config.workbook_name,
                columns: this.config.columns,
                symbols: this.config.symbols,
                options: this.config.options,
                save_config: saveConfig
            };

            // Use XMLHttpRequest for binary download
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/auditoria/api/generate-template/', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.responseType = 'blob';

            xhr.onload = function() {
                if (xhr.status === 200) {
                    // Extract filename from Content-Disposition header
                    const disposition = xhr.getResponseHeader('Content-Disposition');
                    let filename = 'template.xlsx';
                    if (disposition && disposition.indexOf('filename=') !== -1) {
                        const filenameMatch = disposition.match(/filename="(.+)"/);
                        if (filenameMatch) filename = filenameMatch[1];
                    }

                    // Create download link
                    const blob = xhr.response;
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);

                    alert('Plantilla descargada exitosamente');
                    $('#templateCreatorModal').modal('hide');
                } else {
                    alert('Error al generar la plantilla');
                }

                $('#downloadTemplateBtn').prop('disabled', false);
                $('#downloadProgress').hide();
            };

            xhr.onerror = function() {
                alert('Error de conexión');
                $('#downloadTemplateBtn').prop('disabled', false);
                $('#downloadProgress').hide();
            };

            xhr.send(JSON.stringify(payload));

        } catch (error) {
            alert('Error al descargar la plantilla');
            $('#downloadTemplateBtn').prop('disabled', false);
            $('#downloadProgress').hide();
        }
    }

    // ══════════════════════════════════════════════════════════════════════════
    // Wizard Navigation
    // ══════════════════════════════════════════════════════════════════════════

    async nextStep() {
        // Validate current step
        if (!await this.validateStep(this.currentStep)) {
            return;
        }

        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateWizardUI();

            if (this.currentStep === 4) {
                this.updatePreviewSummary();
            }
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateWizardUI();
        }
    }

    async validateStep(step) {
        switch (step) {
            case 1:
                if (!this.config.workbook_name) {
                    alert('Por favor ingrese un nombre de libro de trabajo');
                    return false;
                }
                return true;

            case 2:
                if (this.config.columns.length < 2) {
                    alert('Se requieren al menos 2 columnas');
                    return false;
                }
                // Check for empty column names
                const emptyColumns = this.config.columns.filter(c => !c.name.trim());
                if (emptyColumns.length > 0) {
                    alert('Todas las columnas deben tener un nombre');
                    return false;
                }
                return true;

            case 3:
                if (this.config.symbols.length < 30) {
                    alert('Se requieren al menos 30 símbolos seleccionados');
                    return false;
                }
                return true;

            default:
                return true;
        }
    }

    updateWizardUI() {
        // Update steps visibility
        $('.wizard-step').hide();
        $(`#step${this.currentStep}`).show();

        // Update step indicators
        $('.step-indicator').removeClass('active completed');
        for (let i = 1; i < this.currentStep; i++) {
            $(`.step-indicator[data-step="${i}"]`).addClass('completed');
        }
        $(`.step-indicator[data-step="${this.currentStep}"]`).addClass('active');

        // Update navigation buttons
        $('#prevStepBtn').toggle(this.currentStep > 1);
        $('#nextStepBtn').toggle(this.currentStep < this.totalSteps);
    }

    resetWizard() {
        this.currentStep = 1;
        this.config = {
            workbook_name: '',
            columns: [],
            symbols: [],
            options: {
                include_headers: true,
                include_instructions: true,
                color_code_symbols: true,
                add_data_validation: false
            }
        };

        $('#workbookName').val('').removeClass('is-valid is-invalid');
        $('#workbookNameFeedback').hide();
        $('#workbookNameSuggestions').hide();
        $('#columnsContainer').empty();
        $('.symbol-card').removeClass('selected').find('input[type="checkbox"]').prop('checked', false);
        this.updateSymbolCounter();

        this.addDefaultColumns();
        this.updateWizardUI();
    }
}

// Initialize on page load
$(document).ready(function() {
    // Get audit ID from data attribute or URL
    const auditId = $('#templateCreatorModal').data('audit-id') ||
                     window.location.pathname.match(/detalle\/(\d+)/)?.[1];

    if (auditId) {
        window.templateCreator = new TemplateCreator(parseInt(auditId));
    }
});
