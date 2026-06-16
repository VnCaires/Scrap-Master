# Guia da IA para Desenvolvimento do Projeto AutoApply LLM

## 1. Visão geral

Este projeto tem como objetivo construir um sistema robusto para encontrar vagas na internet, comparar cada vaga com uma palavra-chave ou objetivo profissional definido pelo usuário, interpretar os requisitos da vaga, preencher formulários de candidatura e anexar automaticamente um currículo em PDF.

A ideia central é criar um assistente de candidatura com automação controlada. Ele deve ajudar o usuário a ganhar velocidade, mas sem agir de forma irresponsável, enganosa ou contrária às regras das plataformas. Sempre que houver risco de erro, ambiguidade, pagamento, aceite legal, pergunta sensível ou ação irreversível, o sistema deve pedir confirmação humana antes de enviar.

## 2. Princípios obrigatórios do projeto

### 2.1. Segurança e conformidade

O sistema deve:

1. Respeitar os Termos de Uso dos sites de vagas.
2. Não burlar CAPTCHA, bloqueios anti-bot, paywalls, login indevido, limites de acesso ou mecanismos de proteção.
3. Não inventar informações sobre o usuário.
4. Não responder perguntas de candidatura com dados falsos.
5. Não se candidatar em massa sem controle.
6. Manter logs claros de tudo o que foi encontrado, interpretado, preenchido e enviado.
7. Permitir modo de revisão antes do envio final.
8. Proteger dados sensíveis do usuário, como currículo, telefone, e-mail, endereço e histórico profissional.
9. Nunca armazenar credenciais em texto puro.
10. Permitir que o usuário configure quais sites são permitidos.

### 2.2. Princípio de revisão humana

A primeira versão do projeto deve funcionar com `human-in-the-loop`.

Isso significa que a IA pode encontrar vagas, ranquear, interpretar, abrir formulários e sugerir preenchimentos, mas o envio final da candidatura deve passar por aprovação do usuário.

Depois que o sistema estiver estável, pode ser criado um modo mais automático, mas apenas para sites e tipos de vagas previamente aprovados pelo usuário.

### 2.3. Robustez acima de velocidade

O projeto deve priorizar:

1. Clareza.
2. Logs úteis.
3. Testes.
4. Recuperação de erros.
5. Modularidade.
6. Facilidade de depuração.
7. Reprodutibilidade.

Velocidade vem depois.

## 3. Escopo do MVP

O MVP não deve tentar automatizar todos os sites do mundo. Ele deve começar pequeno, confiável e extensível.

### 3.1. Funcionalidades do MVP

O MVP deve:

1. Receber uma palavra-chave ou objetivo profissional.
2. Receber dados do usuário em um perfil estruturado.
3. Receber um currículo em PDF.
4. Consultar fontes de vagas configuradas.
5. Extrair informações básicas das vagas.
6. Usar LLM para interpretar e normalizar as vagas.
7. Calcular compatibilidade entre vaga e objetivo do usuário.
8. Gerar ranking das melhores vagas.
9. Abrir a página de candidatura.
10. Identificar campos do formulário.
11. Sugerir valores para os campos.
12. Anexar o currículo em PDF quando permitido.
13. Mostrar uma tela ou relatório de revisão.
14. Enviar apenas após confirmação explícita.
15. Salvar histórico de candidaturas.

### 3.2. Fora do escopo do MVP

A primeira versão não deve:

1. Burlar CAPTCHA.
2. Fazer login automaticamente em sites desconhecidos.
3. Comprar créditos ou planos.
4. Criar contas automaticamente.
5. Responder testes técnicos complexos.
6. Fazer entrevistas automatizadas.
7. Enviar candidaturas em massa sem aprovação.
8. Manipular sites que proíbem automação.
9. Prometer 100% de preenchimento para qualquer site.

## 4. Arquitetura geral

O sistema será dividido em camadas.

```text
autoapply-llm/
├── app/
│   ├── cli/
│   ├── core/
│   ├── config/
│   ├── llm/
│   ├── sources/
│   ├── browser/
│   ├── forms/
│   ├── documents/
│   ├── ranking/
│   ├── storage/
│   ├── review/
│   ├── security/
│   └── observability/
├── tests/
├── data/
│   ├── input/
│   ├── output/
│   ├── logs/
│   └── cache/
├── prompts/
├── docs/
├── scripts/
├── pyproject.toml
├── .env.example
├── README.md
└── GUIDE_FOR_AI.md
```

## 5. Stack técnica sugerida

### 5.1. Linguagem

Python 3.12 ou superior.

Motivos:

1. Ecossistema forte para automação web.
2. Boas bibliotecas para PDF, scraping, APIs e LLMs.
3. Fácil integração com Playwright.
4. Desenvolvimento rápido.

### 5.2. Automação de navegador

Usar Playwright.

Motivos:

1. Funciona bem com Chromium, Firefox e WebKit.
2. Suporta navegação moderna.
3. Permite screenshots, tracing e automação robusta.
4. Melhor controle que Selenium em muitos cenários modernos.

### 5.3. Banco de dados local

Começar com SQLite.

Motivos:

1. Simples.
2. Não exige servidor.
3. Bom para MVP.
4. Fácil de migrar para PostgreSQL depois.

### 5.4. ORM

SQLModel ou SQLAlchemy.

### 5.5. Configuração

Usar arquivos YAML/TOML e variáveis de ambiente.

Arquivos sugeridos:

```text
.env
config/settings.yaml
config/sources.yaml
config/profile.yaml
```

### 5.6. LLM

Criar uma camada para LLM usar a API da openAI

A implementação inicial deve pode usar a API configurável por variável de ambiente.

## 6. Módulos do projeto

## 6.1. `app/config`

Responsável por carregar configurações.

Deve ler:

1. Chave da API da LLM.
2. Modelo escolhido.
3. Sites habilitados.
4. Palavra-chave de busca.
5. Local do currículo em PDF.
6. Caminho do banco SQLite.
7. Limites de execução.
8. Modo de revisão.
9. Preferências do usuário.

Exemplo de `settings.yaml`:

```yaml
llm:
  provider: "openai_compatible"
  model: "gpt-4.1-mini"
  temperature: 0.1

runtime:
  headless: false
  max_jobs_per_source: 20
  max_applications_per_run: 3
  require_human_review: true
  screenshot_on_error: true

storage:
  database_url: "sqlite:///data/autoapply.db"

security:
  allow_auto_submit: false
  allowed_domains:
    - "linkedin.com"
    - "indeed.com"
    - "gupy.io"
    - "greenhouse.io"
    - "lever.co"
```

## 6.2. `app/core`

Contém objetos centrais do domínio.

Entidades principais:

1. `UserProfile`
2. `Resume`
3. `JobSource`
4. `JobPosting`
5. `JobMatch`
6. `ApplicationForm`
7. `FormField`
8. `ApplicationDraft`
9. `ApplicationResult`

Exemplo conceitual:

```python
@dataclass
class JobPosting:
    source: str
    url: str
    title: str
    company: str | None
    location: str | None
    remote_type: str | None
    description: str
    requirements: list[str]
    salary: str | None
    raw_html_path: str | None
```

## 6.3. `app/sources`

Responsável por buscar vagas.

Cada fonte deve implementar uma interface comum.

```python
class JobSourceAdapter:
    name: str

    async def search(self, keyword: str, limit: int) -> list[JobPosting]:
        ...
```

Fontes iniciais recomendadas:

1. Greenhouse.
2. Lever.
3. Remotive.
4. Remote OK.
5. Wellfound, se permitido.
6. Gupy, com cuidado por causa de variações de fluxo.
7. LinkedIn e Indeed apenas se as regras e limitações forem respeitadas.

A IA deve preferir APIs públicas, feeds RSS, páginas estáticas e integrações permitidas antes de automação pesada de navegador.

## 6.4. `app/llm`

Responsável por toda interação com a LLM.

Nunca espalhar chamadas de LLM pelo projeto. Toda chamada deve passar por esse módulo.

Funções esperadas:

1. Normalizar descrição da vaga.
2. Extrair requisitos.
3. Classificar senioridade.
4. Identificar tipo de contrato.
5. Avaliar compatibilidade com o perfil.
6. Interpretar campos do formulário.
7. Sugerir respostas para perguntas abertas.
8. Validar se uma resposta foi baseada no perfil do usuário.
9. Detectar riscos antes do envio.

### Regras para respostas da LLM

Sempre que possível, pedir JSON estruturado.

A LLM deve responder com:

1. Campos previsíveis.
2. Score de confiança.
3. Justificativa curta.
4. Lista de incertezas.
5. Indicação de quando pedir revisão humana.

## 6.5. `app/ranking`

Responsável por calcular o quanto uma vaga combina com a busca do usuário.

Critérios sugeridos:

1. Similaridade semântica com a palavra-chave.
2. Compatibilidade com habilidades do usuário.
3. Senioridade.
4. Localidade/remoto.
5. Tipo de contrato.
6. Idioma.
7. Salário, se disponível.
8. Tecnologias exigidas.
9. Requisitos obrigatórios ausentes.
10. Risco ou baixa aderência.

Exemplo de score:

```text
score_final =
  0.30 * similaridade_keyword +
  0.25 * match_habilidades +
  0.15 * senioridade +
  0.10 * localidade +
  0.10 * tipo_contrato +
  0.10 * avaliação_llm
```

O ranking deve ser explicável. Cada vaga deve ter uma justificativa.

## 6.6. `app/browser`

Responsável por controlar o navegador.

Tecnologia sugerida: Playwright assíncrono.

Funções esperadas:

1. Abrir página.
2. Esperar carregamento.
3. Tirar screenshot.
4. Coletar HTML.
5. Identificar formulários.
6. Preencher campos.
7. Anexar arquivos.
8. Detectar erros.
9. Detectar CAPTCHA.
10. Parar quando houver bloqueio ou confirmação sensível.

O módulo de navegador não deve decidir sozinho o que preencher. Ele apenas executa um plano.

## 6.7. `app/forms`

Responsável por mapear campos do formulário para dados do usuário.

Exemplo:

```text
Campo encontrado: "First name"
Tipo: input text
Mapeamento: user_profile.first_name
Confiança: 0.99
```

O módulo deve lidar com:

1. Inputs de texto.
2. Textareas.
3. Selects.
4. Radios.
5. Checkboxes.
6. Uploads.
7. Botões de próximo.
8. Formulários em múltiplas etapas.
9. Campos condicionais.
10. Perguntas abertas.

### Política de preenchimento

Campos simples, como nome, e-mail e telefone, podem ser preenchidos automaticamente se houver alta confiança.

Campos sensíveis, legais ou subjetivos devem pedir revisão.

Exemplos que exigem revisão:

1. Pretensão salarial.
2. Disponibilidade para mudança.
3. Deficiência, raça, gênero ou dados demográficos.
4. Autorização de trabalho.
5. Aceite de termos.
6. Perguntas sobre antecedentes.
7. Perguntas abertas que possam prejudicar o usuário.
8. Qualquer campo com confiança baixa.

## 6.8. `app/documents`

Responsável por lidar com currículo e documentos.

Funções esperadas:

1. Validar existência do PDF.
2. Validar tamanho do arquivo.
3. Extrair texto do currículo.
4. Criar resumo estruturado do currículo.
5. Garantir que a LLM use apenas informações reais do currículo e do perfil.
6. Preparar upload do arquivo.

Ferramentas possíveis:

1. `pypdf`.
2. `pdfplumber`.
3. `python-magic`.
4. `pathlib`.

## 6.9. `app/storage`

Responsável por persistência.

Tabelas sugeridas:

1. `job_postings`
2. `job_matches`
3. `application_attempts`
4. `form_fields`
5. `application_answers`
6. `errors`
7. `screenshots`
8. `run_history`

Cada execução deve ter um `run_id`.

Nada importante deve acontecer sem ser salvo.

## 6.10. `app/review`

Responsável por revisão humana.

Pode começar como CLI interativo e depois virar interface web.

A revisão deve mostrar:

1. Título da vaga.
2. Empresa.
3. Link.
4. Score de compatibilidade.
5. Justificativa.
6. Campos detectados.
7. Valores que serão preenchidos.
8. Perguntas que exigem revisão.
9. Botões ou comandos: aprovar, editar, pular, bloquear domínio, salvar rascunho.

## 6.11. `app/security`

Responsável por políticas de segurança.

Deve conter:

1. Lista de domínios permitidos.
2. Lista de domínios bloqueados.
3. Detecção de CAPTCHA.
4. Detecção de campos sensíveis.
5. Controle de taxa.
6. Política de confirmação antes do envio.
7. Mascaramento de dados nos logs.
8. Validação contra alucinação da LLM.

## 6.12. `app/observability`

Responsável por logs, screenshots, métricas e rastreamento.

Ferramentas sugeridas:

1. `loguru` ou `structlog`.
2. Playwright tracing.
3. Screenshots em erro.
4. JSON logs.

Cada erro deve registrar:

1. Fonte.
2. URL.
3. Etapa.
4. Tipo do erro.
5. Mensagem.
6. Screenshot, se possível.
7. HTML salvo, se permitido.
8. Sugestão de recuperação.

## 7. Fluxo principal do sistema

```text
1. Carregar configurações
2. Carregar perfil do usuário
3. Validar currículo PDF
4. Extrair texto do currículo
5. Buscar vagas nas fontes habilitadas
6. Normalizar vagas com LLM
7. Calcular compatibilidade
8. Salvar ranking
9. Selecionar melhores vagas
10. Para cada vaga:
    10.1 Abrir página
    10.2 Detectar formulário
    10.3 Mapear campos
    10.4 Gerar plano de preenchimento
    10.5 Executar preenchimento
    10.6 Anexar currículo
    10.7 Pausar para revisão humana
    10.8 Enviar se aprovado
    10.9 Salvar resultado
11. Gerar relatório final
```

## 8. Estrutura dos dados do usuário

Criar um arquivo `profile.yaml`.

Exemplo:

```yaml
personal:
  first_name: "Vinicius"
  last_name: "Caires"
  email: "email@example.com"
  phone: "+55 00 00000-0000"
  city: "Salvador"
  country: "Brazil"
  linkedin: ""
  github: ""
  portfolio: ""

preferences:
  target_roles:
    - "Cientista de Dados"
    - "Engenheiro de Machine Learning"
    - "Desenvolvedor Python"
  keywords:
    - "LLM"
    - "Machine Learning"
    - "Python"
  remote_only: true
  relocation: false
  contract_types:
    - "CLT"
    - "PJ"
    - "Remote"
  minimum_salary: null

experience:
  years_total: null
  seniority: null
  skills:
    - "Python"
    - "Machine Learning"
    - "APIs"
    - "Automação"
    - "SQL"
  languages:
    portuguese: "native"
    english: "intermediate"

answers:
  work_authorization: ""
  salary_expectation: ""
  notice_period: ""
  cover_letter_template: ""
```

Campos vazios nunca devem ser inventados. Se a vaga pedir um campo vazio, o sistema deve marcar para revisão.

## 9. Esquemas JSON para LLM

## 9.1. Normalização de vaga

```json
{
  "title": "string",
  "company": "string|null",
  "location": "string|null",
  "remote_type": "remote|hybrid|onsite|unknown",
  "seniority": "intern|junior|mid|senior|lead|unknown",
  "contract_type": "full_time|part_time|contract|internship|temporary|unknown",
  "required_skills": ["string"],
  "nice_to_have_skills": ["string"],
  "responsibilities": ["string"],
  "salary": "string|null",
  "language_requirements": ["string"],
  "red_flags": ["string"],
  "summary": "string",
  "confidence": 0.0
}
```

## 9.2. Avaliação de compatibilidade

```json
{
  "keyword_similarity": 0.0,
  "skills_match": 0.0,
  "seniority_match": 0.0,
  "location_match": 0.0,
  "overall_score": 0.0,
  "matched_reasons": ["string"],
  "missing_requirements": ["string"],
  "risks": ["string"],
  "should_apply": true,
  "requires_human_review": true
}
```

## 9.3. Mapeamento de formulário

```json
{
  "fields": [
    {
      "field_id": "string",
      "label": "string",
      "html_name": "string|null",
      "input_type": "text|email|tel|textarea|select|radio|checkbox|file|unknown",
      "mapped_profile_key": "string|null",
      "proposed_value": "string|null",
      "confidence": 0.0,
      "requires_human_review": true,
      "reason": "string"
    }
  ],
  "submit_button_selector": "string|null",
  "risks": ["string"],
  "confidence": 0.0
}
```

## 10. Prompts base

## 10.1. Prompt de normalização de vaga

```text
Você é um parser de vagas de emprego. Extraia informações estruturadas da vaga abaixo.

Regras:
- Responda somente JSON válido.
- Não invente informações.
- Se algo não estiver claro, use null ou "unknown".
- Separe requisitos obrigatórios de diferenciais.
- Aponte possíveis red flags.
- Dê uma confiança de 0 a 1.

Vaga:
{{job_text}}

Schema esperado:
{{schema}}
```

## 10.2. Prompt de compatibilidade

```text
Você é um avaliador de compatibilidade entre currículo e vaga.

Regras:
- Use apenas os dados do perfil, currículo e vaga.
- Não invente experiências, empresas, certificações ou habilidades.
- Explique os principais motivos do score.
- Liste requisitos ausentes.
- Marque requires_human_review=true quando houver incerteza.
- Responda somente JSON válido.

Perfil:
{{profile}}

Resumo do currículo:
{{resume_summary}}

Vaga normalizada:
{{normalized_job}}

Palavra-chave principal:
{{keyword}}

Schema esperado:
{{schema}}
```

## 10.3. Prompt de preenchimento de formulário

```text
Você é um assistente de preenchimento de formulários de candidatura.

Regras:
- Use apenas dados reais fornecidos no perfil e currículo.
- Não invente dados.
- Não aceite termos legais automaticamente.
- Não responda campos sensíveis sem revisão humana.
- Se a pergunta for ambígua, marque requires_human_review=true.
- Responda somente JSON válido.

Perfil:
{{profile}}

Resumo do currículo:
{{resume_summary}}

Vaga:
{{normalized_job}}

Campos detectados:
{{detected_fields}}

Schema esperado:
{{schema}}
```

## 11. Estratégia contra bugs comuns

## 11.1. Site mudou o HTML

Solução:

1. Evitar seletores frágeis.
2. Preferir labels, roles ARIA e texto visível.
3. Salvar screenshot e HTML no erro.
4. Criar adaptadores por site.
5. Ter testes com páginas HTML salvas.

## 11.2. Campo não identificado

Solução:

1. Usar heurísticas locais.
2. Pedir ajuda da LLM.
3. Se confiança continuar baixa, mandar para revisão.
4. Nunca preencher campo incerto automaticamente.

## 11.3. Upload de PDF falhou

Solução:

1. Verificar seletor `input[type=file]`.
2. Validar tamanho e extensão.
3. Tentar localizar upload por label.
4. Registrar erro com screenshot.
5. Pedir ação manual quando necessário.

## 11.4. Formulário em múltiplas etapas

Solução:

1. Criar estado de formulário.
2. Detectar botão `Next`, `Continue`, `Próximo`, `Avançar`.
3. Preencher etapa atual.
4. Reanalisar DOM após cada etapa.
5. Parar em perguntas sensíveis ou termos.

## 11.5. CAPTCHA ou bloqueio anti-bot

Solução:

1. Detectar CAPTCHA.
2. Parar automação.
3. Informar que intervenção humana é necessária.
4. Não tentar burlar.

## 11.6. LLM respondeu JSON inválido

Solução:

1. Validar com Pydantic.
2. Tentar uma correção automática de JSON.
3. Reexecutar prompt uma vez com erro explícito.
4. Se falhar, salvar erro e pular item.

## 11.7. LLM inventou informação

Solução:

1. Usar validação contra perfil e currículo.
2. Marcar respostas não verificáveis para revisão.
3. Nunca permitir autopreenchimento de resposta aberta sem fonte.
4. Logar campos suspeitos.

## 11.8. Site exige login

Solução:

1. Usar sessão já autenticada pelo usuário, quando permitido.
2. Nunca armazenar senha em texto puro.
3. Permitir que o usuário faça login manual no navegador.
4. Reutilizar estado de navegador salvo de forma segura.
5. Parar se o site bloquear automação.

## 12. Estratégia de desenvolvimento por fases

## Fase 0: Preparação

Objetivo: criar a fundação do projeto.

Entregáveis:

1. Estrutura de pastas.
2. `pyproject.toml`.
3. `.env.example`.
4. Logger.
5. Config loader.
6. Modelos Pydantic.
7. Banco SQLite inicial.
8. CLI básica.

Critério de pronto:

1. Rodar `autoapply --help`.
2. Carregar config sem erro.
3. Criar banco local.
4. Registrar logs.

## Fase 1: Currículo e perfil

Objetivo: preparar dados confiáveis do usuário.

Entregáveis:

1. Leitor de PDF.
2. Validador de currículo.
3. Parser de `profile.yaml`.
4. Geração de resumo estruturado do currículo.
5. Testes.

Critério de pronto:

1. O sistema lê o currículo.
2. O sistema não quebra com PDF inválido.
3. O sistema gera resumo sem inventar dados.

## Fase 2: Coleta de vagas

Objetivo: buscar vagas de fontes simples e permitidas.

Entregáveis:

1. Interface `JobSourceAdapter`.
2. Primeiro adaptador de fonte.
3. Cache de resultados.
4. Normalização básica.
5. Testes com HTML/API mockados.

Critério de pronto:

1. Buscar pelo menos 20 vagas.
2. Salvar vagas no banco.
3. Evitar duplicatas por URL.

## Fase 3: Interpretação com LLM

Objetivo: transformar texto livre em dados estruturados.

Entregáveis:

1. `LLMClient`.
2. Prompts versionados.
3. Schemas Pydantic.
4. Validação de JSON.
5. Retry controlado.
6. Logs de custo/tokens, se disponível.

Critério de pronto:

1. Normalizar vagas.
2. Calcular compatibilidade.
3. Gerar ranking explicável.

## Fase 4: Automação de formulário

Objetivo: abrir uma vaga e preencher um formulário com revisão.

Entregáveis:

1. Playwright browser manager.
2. Detector de campos.
3. Mapeador de campos.
4. Executor de preenchimento.
5. Upload de currículo.
6. Screenshots.

Critério de pronto:

1. Preencher um formulário de teste local.
2. Anexar PDF em formulário de teste.
3. Pausar antes de enviar.

## Fase 5: Revisão humana

Objetivo: permitir controle do usuário.

Entregáveis:

1. Relatório de candidatura.
2. CLI de aprovação.
3. Edição de campos antes do envio.
4. Registro do resultado.

Critério de pronto:

1. Usuário consegue aprovar, editar ou pular.
2. Sistema salva decisão.
3. Sistema não envia sem confirmação.

## Fase 6: Expansão de fontes

Objetivo: adicionar sites reais gradualmente.

Entregáveis:

1. Adaptadores por plataforma.
2. Estratégia de login manual quando permitido.
3. Testes de regressão.
4. Configuração por domínio.

Critério de pronto:

1. Cada fonte tem testes próprios.
2. Erros são isolados por fonte.
3. Uma fonte quebrada não derruba o sistema inteiro.

## Fase 7: Interface web opcional

Objetivo: melhorar a experiência.

Entregáveis:

1. Dashboard local.
2. Ranking visual.
3. Tela de revisão.
4. Histórico de candidaturas.
5. Configuração de perfil.

Stack sugerida:

1. FastAPI.
2. Jinja2 ou React.
3. SQLite/PostgreSQL.

## 13. Comandos CLI esperados

```bash
autoapply init
autoapply validate-profile --profile config/profile.yaml
autoapply parse-resume --pdf data/input/resume.pdf
autoapply search --keyword "Python LLM" --limit 20
autoapply rank --keyword "Python LLM"
autoapply review
autoapply apply --job-id 123
autoapply run --keyword "Machine Learning Engineer" --limit 10
```

## 14. Convenções de código

1. Código claro é mais importante que código curto.
2. Usar type hints.
3. Usar Pydantic para validar dados externos.
4. Toda função que acessa rede deve lidar com timeout.
5. Todo erro importante deve ser logado.
6. Não misturar scraping, LLM e banco na mesma função.
7. Evitar variáveis globais.
8. Testar módulos críticos.
9. Criar mocks para LLM e páginas web.
10. Escrever mensagens de erro úteis.

## 15. Testes obrigatórios

## 15.1. Testes unitários

Cobrir:

1. Config loader.
2. Parser de currículo.
3. Normalização de vaga.
4. Ranking.
5. Mapeamento de campos.
6. Validação de segurança.

## 15.2. Testes de integração

Cobrir:

1. Busca de vagas em fonte mockada.
2. Chamada de LLM mockada.
3. Preenchimento em formulário HTML local.
4. Upload de PDF em formulário local.
5. Fluxo de revisão.

## 15.3. Testes end-to-end

Criar uma página local de candidatura fake para testar o fluxo completo.

Exemplo:

```text
tests/fixtures/job_form.html
```

O sistema deve abrir essa página, preencher os campos, anexar um PDF de teste e parar antes do envio.

## 16. Banco de dados inicial

Tabelas sugeridas:

```sql
CREATE TABLE job_postings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT,
    normalized_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE job_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    score REAL NOT NULL,
    reasons_json TEXT NOT NULL,
    missing_requirements_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES job_postings(id)
);

CREATE TABLE application_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    review_required INTEGER NOT NULL,
    submitted_at TEXT,
    result_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES job_postings(id)
);
```

## 17. Política de logs

Nunca logar:

1. Chaves de API.
2. Senhas.
3. Cookies completos.
4. Tokens de sessão.
5. Dados sensíveis sem máscara.

Pode logar com máscara:

1. E-mail.
2. Telefone.
3. Nome.
4. Caminho local do currículo.

Exemplo:

```text
email: v***@example.com
phone: +55 *** ***-0000
```

## 18. Variáveis de ambiente

Criar `.env.example`:

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=replace_me
LLM_BASE_URL=
LLM_MODEL=gpt-4.1-mini

AUTOAPPLY_DATABASE_URL=sqlite:///data/autoapply.db
AUTOAPPLY_HEADLESS=false
AUTOAPPLY_REQUIRE_HUMAN_REVIEW=true
AUTOAPPLY_ALLOW_AUTO_SUBMIT=false
```

## 19. Definition of Done geral

Uma funcionalidade só está pronta quando:

1. Tem teste.
2. Tem log útil.
3. Lida com erro previsível.
4. Não inventa dado do usuário.
5. Respeita a política de revisão.
6. Está documentada.
7. Funciona com configuração limpa.
8. Não quebra o fluxo principal.

## 20. Backlog inicial

## Prioridade alta

1. Criar estrutura do projeto.
2. Criar modelos Pydantic.
3. Criar loader de configuração.
4. Criar logger.
5. Criar leitor de PDF.
6. Criar `profile.yaml`.
7. Criar cliente LLM abstrato.
8. Criar prompts versionados.
9. Criar adaptador de fonte mockada.
10. Criar ranking inicial.
11. Criar formulário HTML local para testes.
12. Criar automação Playwright para formulário local.
13. Criar revisão humana antes de envio.

## Prioridade média

1. Adicionar fontes reais permitidas.
2. Criar cache de páginas.
3. Criar dashboard local.
4. Criar relatório em Markdown.
5. Criar controle de custo da LLM.
6. Criar deduplicação avançada.
7. Criar detector de red flags.
8. Criar comparador entre versões de currículo.

## Prioridade baixa

1. Interface web completa.
2. Multiusuário.
3. PostgreSQL.
4. Fila assíncrona.
5. Deploy em servidor.
6. Extensão de navegador.
7. Suporte a múltiplos currículos.

## 21. Primeira tarefa recomendada para a IA desenvolvedora

A primeira implementação deve criar apenas a base do projeto.

Tarefa:

```text
Crie a estrutura inicial do projeto autoapply-llm em Python, usando pyproject.toml, Pydantic, Typer para CLI, Loguru para logs e Playwright como dependência planejada. Implemente:

1. Estrutura de pastas.
2. app/config/settings.py
3. app/core/models.py
4. app/cli/main.py
5. .env.example
6. config/settings.example.yaml
7. config/profile.example.yaml
8. tests/test_config.py
9. README.md inicial.

Não implemente scraping real ainda. Crie apenas uma fonte mockada para validar o fluxo.
```

## 22. Regra permanente para a IA durante o desenvolvimento

Sempre que alterar código, entregar o arquivo completo alterado, não apenas trechos.

Sempre que surgir um bug:

1. Explicar a causa provável em linguagem simples.
2. Propor correção.
3. Aplicar correção no arquivo completo.
4. Sugerir teste que comprova a correção.
5. Evitar remendos frágeis.
6. Atualizar documentação quando necessário.

## 23. Decisões pendentes para o usuário

Antes de avançar para implementação real, confirmar:

1. Qual API de LLM será usada.
2. Qual sistema operacional será usado para rodar o projeto.
3. Quais sites de vagas devem ser priorizados.
4. Se o currículo e o perfil ficarão apenas localmente.
5. Se a primeira interface será CLI ou web.
6. Se o envio final deve ser sempre manual no início.
7. Quais tipos de vagas são desejados.
8. Quais campos do perfil o usuário autoriza preencher automaticamente.

## 24. Orientação final

Este projeto deve ser desenvolvido como um assistente confiável de candidatura, não como um robô agressivo de spam.

A meta é economizar tempo do usuário, reduzir trabalho repetitivo e aumentar qualidade das candidaturas. O sistema deve ser transparente, auditável e cuidadoso.

A ordem correta é:

```text
confiabilidade → segurança → revisão humana → automação → escala
```
