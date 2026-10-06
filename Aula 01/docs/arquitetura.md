# Arquitetura

O projeto utiliza uma arquitetura web simples baseada em Flask.

- `app.py`: aplicação, modelos, rotas, autenticação e regras de negócio.
- `templates/`: páginas HTML renderizadas pelo servidor.
- `static/`: CSS e JavaScript.
- SQLite: persistência local.
- SQLAlchemy: camada ORM.

A escolha prioriza simplicidade e facilidade de execução em ambiente acadêmico, sem exigir infraestrutura externa.
