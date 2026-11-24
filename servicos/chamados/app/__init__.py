"""Serviço de Chamados: abrir, atribuir, acompanhar e resolver chamados.

Não acessa o banco de ninguém: confere técnicos e equipamentos chamando os
serviços de Usuários e Inventário por HTTP, e avisa o serviço de Notificações
publicando eventos em uma fila (Redis).
"""
