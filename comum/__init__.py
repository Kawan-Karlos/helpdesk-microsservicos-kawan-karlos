"""Biblioteca compartilhada pelos microsserviços do HelpDesk.

Só tem código técnico (token, cabeçalhos de segurança, erros). Nenhuma regra
de negócio e nenhum acesso ao banco de outro serviço: cada serviço continua
dono dos seus dados.
"""
