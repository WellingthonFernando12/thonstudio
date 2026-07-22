#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TH Auth Middleware V1.0
=======================
Sistema de login simples via variável de ambiente.
Protege TODAS as rotas do Flask. Se THON_AUTH_PASSWORD estiver definida,
todas as requisicoes precisam enviar o header 'X-THON-Auth' com a senha.

Uso:
1. Defina a variavel de ambiente THON_AUTH_PASSWORD no Render (ex: thon123)
2. O frontend (prospector.html) ja envia o header automaticamente
3. Sem a senha, todas as rotas retornam 401 Unauthorized

Se THON_AUTH_PASSWORD nao estiver definida, o sistema fica aberto (modo dev local).
"""
import os
from functools import wraps
from flask import request, jsonify

def get_auth_password():
    return os.environ.get("THON_AUTH_PASSWORD", "").strip()

def is_auth_enabled():
    return bool(get_auth_password())

def check_auth():
    """Verifica se a requisicao atual esta autenticada."""
    if not is_auth_enabled():
        return True  # modo dev: sem senha
    
    # Aceita header X-THON-Auth
    auth_header = request.headers.get("X-THON-Auth", "").strip()
    if auth_header and auth_header == get_auth_password():
        return True
    
    # Aceita query param ?auth=senha (pra facilitar testes no navegador)
    auth_param = request.args.get("auth", "").strip()
    if auth_param and auth_param == get_auth_password():
        return True
    
    return False

def require_auth(f):
    """Decorator para proteger rotas especificas (se precisar)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_auth():
            return jsonify({"ok": False, "error": "Unauthorized", "message": "Acesso negado. Forneça a senha no header X-THON-Auth."}), 401
        return f(*args, **kwargs)
    return decorated

def setup_auth_middleware(app):
    """Registra o before_request no app Flask para proteger tudo."""
    @app.before_request
    def _check_auth_before_request():
        if not is_auth_enabled():
            return None  # modo dev: libera tudo
        
        # Libera arquivos estaticos e a propria pagina de login
        allowed_paths = ["/", "/login", "/auth", "/static", "/_base.css"]
        for path in allowed_paths:
            if request.path == path or request.path.startswith(path):
                return None
        
        # Libera se tiver o header/param de auth
        if check_auth():
            return None
        
        # Se nao tem auth, bloqueia
        return jsonify({"ok": False, "error": "Unauthorized", "message": "Acesso negado."}), 401
