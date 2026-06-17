# Guia da IA para Desenvolvimento do Projeto Scrap Master

Este arquivo e uma referencia viva do projeto. Ele deve ser atualizado sempre que a implementacao mudar de forma relevante, para que novas interacoes em sequencia partam do estado real do repositorio.

## 1. Objetivo do projeto

O Scrap Master e um assistente local de candidatura com `human-in-the-loop`.

Objetivo do produto:

1. Receber perfil, preferencias e curriculo do usuario.
2. Buscar vagas em fontes permitidas.
3. Interpretar e ranquear vagas.
4. Preparar candidatura com revisao humana obrigatoria.
5. So enviar com confirmacao explicita.

O projeto nao deve agir como bot agressivo de spam. A ordem correta continua sendo:

```text
confiabilidade -> seguranca -> revisao humana -> automacao -> escala
```

## 2. Invariantes obrigatorios

Estas regras valem para qualquer implementacao futura:

1. Nao burlar CAPTCHA, bloqueios anti-bot, login indevido ou protecoes da plataforma.
2. Nao inventar dados do usuario.
3. Nao responder perguntas sensiveis ou legais sem revisao humana.
4. Nao enviar candidatura automaticamente na versao atual.
5. Nao armazenar credenciais em texto puro.
6. Mascarar dados sensiveis em logs sempre que possivel.

Hoje essas restricoes aparecem diretamente no codigo:

1. `require_human_review` precisa permanecer `true`.
2. `allow_auto_submit` precisa permanecer `false`.
3. O provider de LLM suportado e `mock` ou `openai_compatible`.

## 3. Estado atual do repositorio

Fases implementadas ate agora:

1. Fase 0: base do projeto.
2. Fase 1: perfil e parser inicial de curriculo.
3. Fase 2: busca mockada com persistencia SQLite.
4. Fase 3: cliente LLM abstrato, prompts, schemas e ranking explicavel.
5. Fase 4 parcial: inspecao local de formulario com Playwright e revisao CLI sem envio.

O que ja existe:

1. `pyproject.toml` com `Typer`, `Pydantic`, `Loguru`, `SQLModel`, `pypdf`, `httpx` e `Playwright` como dependencia opcional.
2. Loader de configuracao via YAML + variaveis de ambiente.
3. Modelos centrais em `app/core/models.py`.
4. Parser de curriculo PDF em `app/documents/resume.py`.
5. Cliente LLM mockado e cliente OpenAI-compativel em `app/llm/client.py`.
6. Schemas Pydantic para normalizacao e compatibilidade em `app/llm/schemas.py`.
7. Prompts versionados em `prompts/`.
8. Storage em SQLite com `SQLModel` e deduplicacao por URL em `app/storage/`.
9. Ranking local explicavel em `app/ranking/scoring.py`.
10. Fonte mockada e registry simples de fontes em `app/sources/`.
11. CLI funcional em `app/cli/main.py`.
12. Inspecao local segura de formulario em `app/browser/`.
13. Mapeamento conservador de campos em `app/forms/`.
14. Rascunho de revisao CLI em `app/review/`.
15. Suite de testes cobrindo config, CLI, storage, ranking, LLM, documentos, browser, forms e review.

O que ainda NAO existe:

1. Scraping real.
2. Login manual assistido.
3. Normalizacao real de vagas usando LLM no fluxo de busca.
4. Automacao Playwright em sites reais.
5. Preenchimento real de formulario.
6. Revisao humana com edicao de respostas.
7. Envio final de candidatura.

## 4. Estrutura atual importante

```text
app/
  cli/
  config/
  core/
  documents/
  llm/
  observability/
  ranking/
  review/
  security/
  sources/
  storage/
tests/
config/
prompts/
data/
```

Modulos relevantes hoje:

1. `app/config/settings.py`
   Carrega settings, profile e invariantes de seguranca.
2. `app/documents/resume.py`
   Valida PDF, tamanho e extrai texto com `pypdf`.
3. `app/llm/client.py`
   Expoe `LLMClient`, `MockLLMClient`, `OpenAICompatibleLLMClient` e factory.
4. `app/ranking/scoring.py`
   Calcula score local e gera `JobMatch` explicavel.
5. `app/storage/`
   Contem schema, engine, sessao e repositorio SQLite.
6. `app/cli/main.py`
   Orquestra os fluxos atuais.
7. `app/browser/`
   Abre paginas locais/teste com Playwright para inspecao sem submit.
8. `app/forms/`
   Detecta e mapeia campos para valores seguros do perfil.
9. `app/review/`
   Monta rascunho de revisao e normaliza decisoes CLI.

## 5. Configuracao atual

Arquivos de exemplo atuais:

```text
.env.example
config/settings.example.yaml
config/profile.example.yaml
```

Observacoes importantes:

1. O exemplo padrao usa `llm.provider=mock` para desenvolvimento offline.
2. O banco padrao continua sendo `sqlite:///data/scrap_master.db`.
3. O padrao operacional agora usa `config/settings.yaml` e `config/profile.yaml`.
4. `profile_path` no settings local aponta para `config/profile.yaml`.
5. `resume_pdf_path` continua sendo apenas uma referencia; o parser valida no momento de uso.

Variaveis de ambiente relevantes:

```env
LLM_PROVIDER=mock
LLM_API_KEY=replace_me
LLM_BASE_URL=
LLM_MODEL=gpt-4.1-mini
SCRAP_MASTER_DATABASE_URL=sqlite:///data/scrap_master.db
SCRAP_MASTER_HEADLESS=false
SCRAP_MASTER_REQUIRE_HUMAN_REVIEW=true
SCRAP_MASTER_ALLOW_AUTO_SUBMIT=false
```

## 6. Fluxo real disponivel hoje

Fluxo implementado no momento:

```text
1. Carregar settings
2. Carregar profile
3. Inicializar banco SQLite
4. Buscar vagas nas fontes habilitadas
5. Persistir vagas com deduplicacao por URL
6. Gerar avaliacao de compatibilidade via LLM mock ou provider OpenAI-compativel
7. Ranquear vagas localmente
8. Salvar matches e historico de execucao
9. Encerrar antes de qualquer browser automation em site real
```

Fluxo de curriculo hoje:

```text
1. Validar caminho do PDF
2. Validar extensao .pdf
3. Validar tamanho maximo
4. Extrair texto com pypdf
5. Retornar erro claro se o arquivo nao puder ser lido
```

Fluxo de formulario local hoje:

```text
1. Abrir fixture HTML local com Playwright
2. Detectar inputs, selects, textareas e botao de submit
3. Mapear campos simples com dados do profile
4. Marcar campos sensiveis para revisao humana
5. Mostrar rascunho na CLI
6. Salvar tentativa como draft, approved ou skipped
7. Nunca clicar em submit
```

## 7. Comandos CLI atuais

Comandos realmente implementados hoje:

```bash
scrap-master --help
scrap-master init
scrap-master init-db --settings config/settings.yaml
scrap-master config-check --settings config/settings.yaml
scrap-master validate-profile --profile config/profile.yaml
scrap-master parse-resume --pdf data/input/resume.pdf
scrap-master search --settings config/settings.yaml --keyword "Python LLM" --limit 5
scrap-master rank --settings config/settings.yaml --keyword "Python LLM"
scrap-master run --settings config/settings.yaml --keyword "Machine Learning Engineer" --limit 10
scrap-master inspect-form --url tests/fixtures/job_form.html
scrap-master review --url tests/fixtures/job_form.html
```

Comandos ainda nao implementados:

1. `scrap-master apply`

## 8. Persistencia atual

Tabelas implementadas hoje:

1. `job_postings`
2. `job_matches`
3. `application_attempts`
4. `run_history`

Comportamentos atuais:

1. Vagas sao deduplicadas por `url`.
2. Matches armazenam score, motivos, riscos e requisitos ausentes.
3. Historico de execucao armazena palavra-chave, quantidade de fontes, vagas e matches.

## 9. LLM e ranking

Camada LLM atual:

1. `MockLLMClient`
   Usado em desenvolvimento e testes.
2. `OpenAICompatibleLLMClient`
   Usa `base_url`, `api_key`, `model` e `httpx`.

Prompts existentes:

1. `prompts/normalize_job.txt`
2. `prompts/evaluate_compatibility.txt`
3. `prompts/map_form.txt`

Estado atual do ranking:

1. Usa similaridade por keyword.
2. Usa match de skills do profile.
3. Usa senioridade.
4. Usa compatibilidade com remoto/local.
5. Usa score complementar da avaliacao LLM.
6. Sempre retorna `requires_human_review=true`.

## 10. Testes e criterio de pronto atual

Status atual:

1. `python -m pytest` passa.
2. A suite cobre config, CLI, documentos, storage, ranking, LLM, browser, forms e review.

Definition of Done para novas features continua sendo:

1. Ter teste.
2. Ter log util.
3. Lidar com erro previsivel.
4. Nao inventar dado do usuario.
5. Respeitar revisao humana.
6. Atualizar documentacao quando necessario.
7. Nao quebrar o fluxo principal.

## 11. Proximos passos recomendados

A proxima etapa natural e completar a Fase 4 com preenchimento local controlado, ainda sem sites reais.

Prioridade recomendada:

1. Implementar preenchimento local em pagina fake.
2. Adicionar upload de PDF em fixture local.
3. Permitir edicao CLI dos valores antes de salvar decisao.
4. Criar screenshots/traces em erro.
5. Preparar detector de CAPTCHA/bloqueio antes de qualquer site real.

## 12. Regra de manutencao deste guia

Sempre que o codigo mudar de forma relevante, atualizar este arquivo com:

1. O que ja existe de verdade.
2. O que ainda nao existe.
3. Quais comandos estao implementados.
4. Quais invariantes de seguranca estao ativas.
5. Qual e a proxima fase recomendada.

Este arquivo deve refletir o estado real do repositorio, nao apenas a intencao original do projeto.
