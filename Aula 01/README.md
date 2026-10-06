# HelpDesk Acadêmico

Sistema web de gerenciamento de chamados desenvolvido para uma atividade de Engenharia de Software.

## Funcionalidades

- Autenticação e logout
- Perfis: Administrador, Agente e Usuário
- Dashboard com indicadores
- Abertura e consulta de chamados
- Busca e filtros
- Prioridades e SLA
- Alteração de status
- Comentários
- Cadastro de usuários
- Exclusão de chamados por administrador
- Persistência em SQLite
- Senhas armazenadas com hash

## Tecnologias

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- HTML5/CSS3
- Jinja2

## Executar localmente

### 1. Criar ambiente virtual

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Executar

```bash
python app.py
```

Acesse http://127.0.0.1:5000

## Usuários de demonstração

Administrador:
- e-mail: admin@helpdesk.local
- senha: Admin123!

Agente:
- e-mail: agente@helpdesk.local
- senha: Agente123!

Usuário:
- e-mail: usuario@helpdesk.local
- senha: Usuario123!

## Regras de negócio

- Usuários comuns só visualizam e comentam seus próprios chamados.
- Agentes podem atualizar o status dos chamados.
- Administradores possuem acesso administrativo completo.
- Todo chamado recebe SLA conforme a prioridade:
  - Baixa: 72h
  - Média: 48h
  - Alta: 24h
  - Crítica: 8h
- Título deve ter pelo menos 5 caracteres.
- Descrição deve ter pelo menos 10 caracteres.
- E-mail de usuário é único.
- Senhas não são armazenadas em texto puro.

## Estrutura

```text
helpdesk-academico/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── docs/
├── static/
└── templates/
```

## Objetivo acadêmico

O projeto demonstra requisitos funcionais e não funcionais, autenticação, autorização, CRUD, regras de negócio, persistência, tratamento de erros e organização arquitetural.
