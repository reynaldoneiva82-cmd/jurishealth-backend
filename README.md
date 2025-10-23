# JurisHealth Backend - API

Backend da plataforma JurisHealth - conecta hospitais privados a oportunidades judiciais de saúde.

## 🚀 Deploy no Render.com

### Método 1: Via GitHub (Recomendado)

1. **Crie um repositório no GitHub**
   - Acesse: https://github.com/new
   - Nome: `jurishealth-backend`
   - Visibilidade: Private ou Public

2. **Faça upload dos arquivos**
   - Faça upload de TODOS os arquivos desta pasta para o repositório
   - Ou use Git:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/SEU_USUARIO/jurishealth-backend.git
   git push -u origin main
   ```

3. **Deploy no Render**
   - Acesse: https://render.com
   - Clique em "New +" → "Web Service"
   - Conecte seu repositório GitHub
   - Configure:
     - **Name:** `jurishealth-api`
     - **Region:** Oregon (US West)
     - **Branch:** `main`
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
     - **Plan:** Free

4. **Adicione Variáveis de Ambiente**
   - Clique em "Environment" → "Add Environment Variable"
   - Adicione:
     ```
     DATABASE_URL = postgresql://usuario:senha@host/database
     SECRET_KEY = sua_chave_secreta_aqui
     JWT_SECRET = outra_chave_secreta_aqui
     ```

5. **Deploy!**
   - Clique em "Create Web Service"
   - Aguarde 5-10 minutos
   - Sua API estará em: `https://jurishealth-api.onrender.com`

### Método 2: Via render.yaml (Blueprint)

1. **Crie o banco de dados primeiro**
   - No Render: "New +" → "PostgreSQL"
   - Name: `jurishealth-db`
   - Plan: Free
   - Copie a "Internal Database URL"

2. **Deploy via Blueprint**
   - No Render: "New +" → "Blueprint"
   - Conecte o repositório
   - O Render lerá automaticamente o `render.yaml`
   - Confirme e faça deploy

## 🧪 Testar a API

Após o deploy:

1. **Health Check**
   ```
   GET https://jurishealth-api.onrender.com/health
   ```
   Deve retornar: `{"status": "ok"}`

2. **Documentação Interativa**
   ```
   https://jurishealth-api.onrender.com/docs
   ```

3. **Registrar Hospital**
   ```bash
   curl -X POST https://jurishealth-api.onrender.com/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Hospital Teste",
       "city": "Belo Horizonte",
       "email": "teste@hospital.com",
       "password": "senha123",
       "specialties": ["Cardiologia"],
       "credentials": ["CNES123"]
     }'
   ```

## 📦 Estrutura do Projeto

```
.
├── app.py              # Aplicação FastAPI principal
├── models.py           # Modelos SQLAlchemy
├── schemas.py          # Schemas Pydantic
├── crud.py             # Operações de banco de dados
├── auth.py             # Autenticação JWT
├── config.py           # Configurações
├── db.py               # Conexão com banco
├── logger.py           # Sistema de logs
├── tasks.py            # Tarefas assíncronas
├── utils.py            # Utilitários
├── requirements.txt    # Dependências Python
├── Procfile            # Comando de inicialização
├── runtime.txt         # Versão do Python
└── render.yaml         # Configuração Render

ingest/                 # Módulos de ingestão de dados
├── tjmg_scraper.py     # Scraper TJMG
├── datajud_api.py      # API DataJud CNJ
└── ...
```

## 🔧 Desenvolvimento Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
export DATABASE_URL="postgresql://user:pass@localhost/jurishealth"
export SECRET_KEY="dev-secret-key"
export JWT_SECRET="dev-jwt-secret"

# Rodar servidor
uvicorn app:app --reload --port 8001
```

Acesse: http://localhost:8001/docs

## 🔒 Segurança

- ✅ Autenticação JWT
- ✅ Hash de senhas com bcrypt
- ✅ Rate limiting
- ✅ CORS configurado
- ✅ Validação de dados com Pydantic
- ✅ SQL injection protection (SQLAlchemy)

## 📊 Banco de Dados

PostgreSQL com as seguintes tabelas:
- `hospitals` - Hospitais cadastrados
- `cases` - Processos judiciais (oportunidades)
- `bids` - Orçamentos enviados
- `awards` - Adjudicações

## 🌐 Endpoints Principais

### Públicos
- `GET /health` - Status da API
- `GET /stats/platform` - Estatísticas gerais
- `POST /auth/register` - Registrar hospital
- `POST /auth/login` - Login
- `GET /opportunities` - Listar oportunidades

### Autenticados
- `GET /hospitals/me` - Dados do hospital
- `POST /bids` - Enviar orçamento
- `GET /hospitals/{id}/bids` - Listar orçamentos
- `GET /hospitals/{id}/stats` - Estatísticas do hospital

### Admin
- `POST /cases/{id}/award` - Adjudicar caso
- `POST /ingest/tjmg/run` - Executar ingestão

## 📝 Licença

Propriedade de JurisHealth © 2025

