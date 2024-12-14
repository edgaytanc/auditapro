from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, logout as logout_func
from django.contrib.auth import login as login_func
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from .const import USER_ERROR_INSTANCES, USER_CLIENT_FIELDS

from .services import (
    create_user as create_user_func,
    delete_user as delete_user_func,
    update_user as update_user_func,
    login_user_service,
)

User = get_user_model()


def login(req):
    if req.method == "GET":
        return login_page(req)
    elif req.method == "POST":
        return login_user(req)


def signup(req):
    if req.method == "GET":
        return signup_page(req)
    elif req.method == "POST":
        return create_user(req)


def create_user(req):
    username = req.POST.get("username")
    first_name = req.POST.get("first_name")
    last_name = req.POST.get("last_name")
    email = req.POST.get("email")
    password_1 = req.POST.get("password_1")
    password_2 = req.POST.get("password_2")

    try:
        create_user_func(username, first_name, last_name, email, password_1, password_2)

        user = authenticate(email=email, password=password_1)

        login_func(req, user)

        messages.success(req, "Usuario creado y autenticado exitosamente.")
        return redirect("user")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return signup_page(req)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, USER_ERROR_INSTANCES):
            messages.error(req, error_message)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
        return signup_page(req)


def login_user(req):
    email = req.POST.get("email")
    password = req.POST.get("password")
    try:
        login_user_service(req, email, password)
        return redirect("user")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return login_page(req)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, USER_ERROR_INSTANCES):
            messages.error(req, error_message)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
        return login_page(req)


@login_required
def logout(req):
    logout_func(req)
    messages.success(req, "Sesión cerrada correctamente.")
    return redirect("home")


@login_required
def edit_user(req, field):
    value = req.POST.get("value")
    try:
        update_user_func(req, value, field)
        messages.success(req, "El campo se ha actualizado correctamente.")
        return redirect("user")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("user")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, USER_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("user")

        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("user")


@login_required
def delete_account(req):
    email = req.POST.get("email")
    password = req.POST.get("password")
    try:
        delete_user_func(req, email, password)
        messages.success(req, "Cuenta eliminada correctamente.")
        return redirect("home")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return user_page(req)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, USER_ERROR_INSTANCES):
            messages.error(req, error_message)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
        return redirect("user")


# Páginas para el front
def index_page(req: HttpRequest):
    if req.user.is_authenticated:
        return render(req, "users/index-system.html")
    else:
        return render(req, "common/home.html")


def login_page(req):
    return render(req, "users/login.html", {})


def signup_page(req):
    return render(req, "users/signup.html", {})


@login_required
def user_page(req):
    data = {
        "user_fields": USER_CLIENT_FIELDS,
    }
    return render(req, "users/user.html", data)


@login_required
def dashboard(req):
    return render(req, "users/dashboard.html", {})
