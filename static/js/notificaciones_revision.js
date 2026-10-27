(function () {
    if (window.__auditaNotificationsReady) return;
    window.__auditaNotificationsReady = true;

    const routes = window.NOTIFICATION_ROUTES || {};

    function getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input && input.value) return input.value;

        const cookie = document.cookie
            .split('; ')
            .find((row) => row.startsWith('csrftoken='));

        return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : '';
    }

    function buildUrl(template, id) {
        if (!template) return '';
        return template.replace('/0/', `/${id}/`);
    }

    async function readJson(response) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return response.json();
        }

        const text = await response.text();
        throw new Error(text || 'El servidor no devolvió una respuesta válida.');
    }

    document.addEventListener('click', async function (event) {
        const reviewButton = event.target.closest('.btn-approve, .btn-reject');
        const deleteButton = event.target.closest('.btn-delete-one');

        if (!reviewButton && !deleteButton) return;

        const csrfToken = getCsrfToken();

        if (deleteButton) {
            const notificationStatusId = deleteButton.dataset.nsid;
            if (!notificationStatusId) return;

            if (!window.confirm('¿Eliminar esta notificación de tu bandeja?')) return;

            deleteButton.disabled = true;

            try {
                const response = await fetch(buildUrl(routes.delete_one, notificationStatusId), {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await readJson(response);
                if (!response.ok || !data.ok) {
                    throw new Error(data.error || 'No fue posible eliminar la notificación.');
                }

                window.location.reload();
            } catch (error) {
                console.error('[Notificaciones] Error al eliminar:', error);
                window.alert(error.message);
                deleteButton.disabled = false;
            }

            return;
        }

        const notificationId = reviewButton.dataset.id;
        if (!notificationId) return;

        const modal = reviewButton.closest('.modal');
        const action = reviewButton.classList.contains('btn-approve') ? 'approve' : 'reject';

        const reasons = modal
            ? Array.from(modal.querySelectorAll('.reason-item:checked')).map((input) => input.value)
            : [];

        const comments = modal?.querySelector('[name="review_comments"]')?.value?.trim() || '';

        if (action === 'reject' && reasons.length === 0 && !comments) {
            window.alert('Para rechazar, indique al menos un motivo o escriba un comentario.');
            return;
        }

        reviewButton.disabled = true;

        try {
            const body = new URLSearchParams();
            body.set('action', action);
            body.set('comments', comments);
            reasons.forEach((reason) => body.append('reasons[]', reason));

            const response = await fetch(buildUrl(routes.review, notificationId), {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
                },
                body: body.toString()
            });

            const data = await readJson(response);
            if (!response.ok || !data.ok) {
                throw new Error(data.error || 'No fue posible registrar la revisión.');
            }

            window.location.reload();
        } catch (error) {
            console.error('[Notificaciones] Error en revisión:', error);
            window.alert(error.message);
            reviewButton.disabled = false;
        }
    });
})();
