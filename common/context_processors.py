from typing import List
from django.http import HttpRequest
from django.urls import reverse
from audits.utils import get_assigned_audits
from common.types import NavBarLink
from tools.models import CurrentStatus, Months


def breadcrumbs_processor(req):
    # Inicializamos la lista de breadcrumbs con la raíz (Home)
    breadcrumbs = [("Inicio", "/")]

    # Caso especial para el dashboard de superadmin
    if req.path.strip("/") == "superadmin/dashboard":
        return {"breadcrumbs": [
            ("Inicio", "/"),
            ("Dashboard", "/superadmin/dashboard"),
        ]}
    
    # Caso especial para las páginas de usuarios cuando el usuario es superadmin
    if req.path.startswith("/superadmin/users") and hasattr(req, 'user') and req.user.is_authenticated and req.user.role.name == "superadmin":
        return {"breadcrumbs": [
            ("Inicio", "/"),
            ("Dashboard", "/superadmin/dashboard"),
            ("Usuarios", req.path),
        ]}

    # Obtenemos la URL actual y la dividimos
    path = req.path.strip("/").split("/")

    # Diccionario de nombres legibles para cada parte de la URL
    path_name_map = {
        "resumen-tiempo": "Resumen de Tiempo",
        "resumen-auditoria": "Resumen de Auditoría",
        "horas-trabajadas": "Horas Trabajadas",
        "papeles-trabajo": "Papeles de Trabajo",
        "archivo_permanente": "Archivo Permanente",
        "notificaciones": "Notificaciones",
        "dashboard": "Dashboard",
        "gestionar_auditores": "Gestionar Auditores",
        "herramientas": "Herramientas",
        "auditorias": "Auditorías",
        "crear": "Crear",
        "borrar": "Borrar",
        "notificaciones": "Notificaciones",
        "marcas-de-auditoria": "Marcas de Auditoría",
        "tipos-de-monedas": "Tipos de Moneda",
        "actividades": "Actividades",
        "superadmin": "Panel Administrativo",
        "users": "Usuarios",
    }

    # Construimos los breadcrumbs dinámicamente basados en la URL
    current_url = "/"
    for part in path:
        if part.isdigit():
            part_name = "Actualizar"
        else:
            part_name = path_name_map.get(part, part.capitalize())

        current_url += f"{part}/"
        breadcrumbs.append((part_name, current_url))

    return {"breadcrumbs": breadcrumbs}


def get_is_active_route(route: str, req: HttpRequest):
    path = req.path
    reverse_url = reverse(route)

    striped_path = path.strip("/")
    striped_reverse_url = reverse_url.strip("/")
    if striped_reverse_url == striped_path:
        return True
    if reverse_url in path and reverse_url != "/":
        return True
    path_splited_list = path.split("/")

    if len(path_splited_list) < 1:
        return False

    for path_segment in path_splited_list:
        if reverse_url == path_segment:
            return True

    return False


def aside_navbar_processor(req: HttpRequest):

    # Verificar si el usuario es administrador en modalidad grupal
    is_group_admin = False
    if req.user.is_authenticated:
        is_group_admin = (req.user.modalidad == 'G' and 
                          req.user.role and 
                          req.user.role.name == "audit_manager")

    nav_bar_links: List[NavBarLink] = [
        {
            "active": get_is_active_route("home", req),
            "icon": """<svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M80 212v236a16 16 0 0016 16h96V328a24 24 0 0124-24h80a24 24 0 0124 24v136h96a16 16 0 0016-16V212" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><path d="M480 256L266.89 52c-5-5.28-16.69-5.34-21.78 0L32 256M400 179V64h-48v69" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>""",
            "name": "Home",
            "type": "anchor",
            "url": "home",
        },
        # {
        #     "active": get_is_active_route("dashboard", req),
        #     "icon": """<svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M32 32v432a16 16 0 0016 16h432" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><rect x="96" y="224" width="80" height="192" rx="20" ry="20" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><rect x="240" y="176" width="80" height="240" rx="20" ry="20" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><rect x="383.64" y="112" width="80" height="304" rx="20" ry="20" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>""",
        #     "name": "Dashboard",
        #     "type": "anchor",
        #     "url": "dashboard",
        # },
    ]
    
    # Solo añadir el enlace de gestión de auditores si el usuario es administrador en modalidad grupal
    if is_group_admin:
        nav_bar_links.append({
            "active": get_is_active_route("manage_auditors", req),
            "icon": """<svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M402 168c-2.93 40.67-33.1 72-66 72s-63.12-31.32-66-72c-3-42.31 26.37-72 66-72s69 30.46 66 72z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><path d="M336 304c-65.17 0-127.84 32.37-143.54 95.41-2.08 8.34 3.15 16.59 11.72 16.59h263.65c8.57 0 13.77-8.25 11.72-16.59C463.85 335.36 401.18 304 336 304z" fill="none" stroke="currentColor" stroke-miterlimit="10" stroke-width="32"/><path d="M200 185.94c-2.34 32.48-26.72 58.06-53 58.06s-50.7-25.57-53-58.06C91.61 152.15 115.34 128 147 128s55.39 24.77 53 57.94z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><path d="M206 306c-18.05-8.27-37.93-11.45-59-11.45-52 0-102.1 25.85-114.65 76.2-1.65 6.66 2.53 13.25 9.37 13.25H154" fill="none" stroke="currentColor" stroke-linecap="round" stroke-miterlimit="10" stroke-width="32"/></svg>""",
            "name": "Gestionar Auditores",
            "type": "anchor",
            "url": "manage_auditors",
        })
    
    # Continuar con el resto de enlaces
    nav_bar_links.extend([
        {
            "active": get_is_active_route("tools", req),
            "icon": """
            <svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M277.42 247a24.68 24.68 0 00-4.08-5.47L255 223.44a21.63 21.63 0 00-6.56-4.57 20.93 20.93 0 00-23.28 4.27c-6.36 6.26-18 17.68-39 38.43C146 301.3 71.43 367.89 37.71 396.29a16 16 0 00-1.09 23.54l39 39.43a16.13 16.13 0 0023.67-.89c29.24-34.37 96.3-109 136-148.23 20.39-20.06 31.82-31.58 38.29-37.94a21.76 21.76 0 003.84-25.2zM478.43 201l-34.31-34a5.44 5.44 0 00-4-1.59 5.59 5.59 0 00-4 1.59h0a11.41 11.41 0 01-9.55 3.27c-4.48-.49-9.25-1.88-12.33-4.86-7-6.86 1.09-20.36-5.07-29a242.88 242.88 0 00-23.08-26.72c-7.06-7-34.81-33.47-81.55-52.53a123.79 123.79 0 00-47-9.24c-26.35 0-46.61 11.76-54 18.51-5.88 5.32-12 13.77-12 13.77a91.29 91.29 0 0110.81-3.2 79.53 79.53 0 0123.28-1.49C241.19 76.8 259.94 84.1 270 92c16.21 13 23.18 30.39 24.27 52.83.8 16.69-15.23 37.76-30.44 54.94a7.85 7.85 0 00.4 10.83l21.24 21.23a8 8 0 0011.14.1c13.93-13.51 31.09-28.47 40.82-34.46s17.58-7.68 21.35-8.09a35.71 35.71 0 0121.3 4.62 13.65 13.65 0 013.08 2.38c6.46 6.56 6.07 17.28-.5 23.74l-2 1.89a5.5 5.5 0 000 7.84l34.31 34a5.5 5.5 0 004 1.58 5.65 5.65 0 004-1.58L478.43 209a5.82 5.82 0 000-8z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>""",
            "name": "Herramientas",
            "type": "anchor",
            "url": "tools",
        },
        {
            "active": get_is_active_route("assigned_audits", req),
            "icon": """<svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M416 221.25V416a48 48 0 01-48 48H144a48 48 0 01-48-48V96a48 48 0 0148-48h98.75a32 32 0 0122.62 9.37l141.26 141.26a32 32 0 019.37 22.62z" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="32"/><path d="M200 128v108a28.34 28.34 0 0028 28h108" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><path d="M176 288h160M176 368h160" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>""",
            "name": "Proyectos Auditoría",
            "type": "anchor",
            "url": "assigned_audits",
        },
        {
            "active": get_is_active_route("notifications", req),
            "icon": """<svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M427.68 351.43C402 320 383.87 304 383.87 217.35 383.87 138 343.35 109.73 310 96c-4.43-1.82-8.6-6-9.95-10.55C294.2 65.54 277.8 48 256 48s-38.21 17.55-44 37.47c-1.35 4.6-5.52 8.71-9.95 10.53-33.39 13.75-73.87 41.92-73.87 121.35C128.13 304 110 320 84.32 351.43 73.68 364.45 83 384 101.61 384h308.88c18.51 0 27.77-19.61 17.19-32.57zM320 384v16a64 64 0 01-128 0v-16" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>""",
            "name": "Notificaciones",
            "type": "collapse",
            "url": "notifications",
            "collapse_values": [
                {
                    "active": get_is_active_route("notifications", req),
                    "name": "Notificaciones",
                    "type": "anchor",
                    "url": "notifications",
                },
                {
                    "active": get_is_active_route("create_notification", req),
                    "name": "Enviar Notificación",
                    "type": "anchor",
                    "url": "create_notification",
                },
            ],
        },
        {
            "active": get_is_active_route("archivo_permanente", req),
            "icon": """<svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M336 264.13V436c0 24.3-19.05 44-42.95 44H107c-23.95 0-43-19.7-43-44V172a44.26 44.26 0 0144-44h94.12a32 32 0 0122.62 9.37l109.15 111a25.4 25.4 0 017.24 17.77z" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="32"/><path d="M200 128v108a28.34 28.34 0 0028 28h108" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><path d="M176 128V76a44.26 44.26 0 0144-44h94a24.83 24.83 0 0117.61 7.36l109.15 111A25.09 25.09 0 01448 168v172c0 24.3-19.05 44-42.95 44H344" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="32"/><path d="M312 32v108a28.34 28.34 0 0028 28h108" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>""",
            "name": "Archivo Permanente",
            "type": "anchor",
            "url": "archivo_permanente",
        },
       {
            "active": get_is_active_route("auditorias", req),
            "icon": """<svg xmlns="http://www.w3.org/2000/svg" class="ionicon" viewBox="0 0 512 512"><path d="M32 32v432a16 16 0 0016 16h432" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><rect x="96" y="224" width="80" height="192" rx="20" ry="20" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><rect x="240" y="176" width="80" height="240" rx="20" ry="20" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/><rect x="383.64" y="112" width="80" height="304" rx="20" ry="20" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="32"/></svg>""",
            "name": "Auditorías",
            "type": "collapse",
            "url": "auditorias",
            "collapse_values": [
                {
                    "active": get_is_active_route("auditoria_financiera", req),
                    "name": "Financiera",
                    "type": "anchor",
                    "url": "auditoria_financiera",
                },
                {
                    "active": get_is_active_route("auditoria_interna", req),
                    "name": "Interna",
                    "type": "anchor",
                    "url": "auditoria_interna",
                },
            ],
        },
    ])

    return {"aside_navbar_links": nav_bar_links}


def assigned_audits(req: HttpRequest):
    return {
        "assigned_audits": (
            get_assigned_audits(req.user.role.name, req)
            if req.user.is_authenticated
            else ""
        )
    }


def is_choose_new_audit_path(req: HttpRequest):
    choose_new_audit_paths = (
        "audit_time_summary_index",
        "audit_time_summary_table",
        "summary_worked_hours_table",
        "status_of_work_papers_table",
        "activities_page",
        "tools",
    )
    for p in choose_new_audit_paths:
        url = reverse(p)
        if req.path == url:
            return {"is_choose_new_audit_path": True}
    return {"is_choose_new_audit_path": False}


def months_processor(req: HttpRequest):
    months = Months.objects.all()
    return {"months": months}


def current_statuses_processor(req: HttpRequest):
    current_statuses = CurrentStatus.objects.all()
    return {"current_statuses": current_statuses}
