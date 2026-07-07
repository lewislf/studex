<a id="titulo"></a>
<h1 align="center"> <img width="384" height="143" alt="studex_logo" src="https://github.com/user-attachments/assets/8e5550fe-fddd-4b15-bc72-21f9f0b3ee93" /> </h1>

<p align="center">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" />
  <img src="https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/🐄PyMuPDF-FF6F00?style=for-the-badge&logo=mupdf&logoColor=white" />
  <img src="https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Mantine-ffffff.svg?style=for-the-badge&logo=Mantine&logoColor=339af0" />
  <img src="https://img.shields.io/badge/react_native-%2320232a.svg?style=for-the-badge&logo=react&logoColor=61DAFB" />
  <img src="https://img.shields.io/badge/Material%20UI-%23FFFFFF.svg?style=for-the-badge&logo=MUI&logoColor=007FFF" />
  <img src="https://img.shields.io/badge/vite-%23646CFF.svg?style=for-the-badge&logo=vite&logoColor=white" />
</p>

## Índice  
* [Início](#titulo) 
* [Descrição do Projeto](#descrição) 
* [Funcionalidades](#funcionalidades)
* [Arquitetura](#arquitetura)
* [Execução](#execução)
* [Como gerar a Documentação do Código](#documentação-do-código) 
* [Testes](#testes)
* [Tecnologias utilizadas](#tecnologias-utilizadas)
* [Diagrama de Classes](#diagrama-de-classes)
* [Telas](#telas)
* [Pessoas Contribuidoras](#contribuidores) 
* [Licença](#licença) 

## Descrição

O sistema tem como objetivo ajudar os alunos a estudar através de resumos,
flashcards, mapas mentais gerados por uma Large Language Model (LLM). Todas
essas funcionalidades estarão em um só lugar de fácil acesso e com o conteúdo
estruturado de forma a priorizar o entendimento da matéria/assunto em questão.
Outro ponto interessante do sistema, é que ele foi idealizado para gamificar os
estudos, utilizando por exemplo um sistema de Hot-Streak/Heatmap, onde o usuário 
deve estudar todos os dias para conseguir manter sua sequência de estudos.

## Funcionalidades

O sistema têm como principais funcionalidades:
- Geração de resumos por uma LLM
- Geração de Mapas Mentais por uma LLM
- Geração Automática de Flashcards por uma LLM
- Geração Manual de Flashcards
- Funcionalidade de Download dos recursos gerados pela aplicação
- Discussão de dúvidas com modelos de IA capazes de serem um tutor
pessoal.
- Sistema de Login/Criar Conta
- Armazenamento dos Conteúdos/FlashCards/Mapas Mentais na conta do
Usuário

## Arquitetura

O sistema está idealizado para plataformas Web, onde o usuário irá entrar no site
da aplicação, enviar um PDF e receber o resumo e as outras funcionalidades do
sistema.

### Fluxo Geral

1. Usuário envia um PDF.
2. O documento é processado pelo PyMuPDF.
3. O conteúdo é indexado no sistema RAG.
4. A LLM gera:
   - Resumos
   - Flashcards
   - Mapas mentais
5. Os conteúdos são armazenados no PostgreSQL.
6. O usuário pode acessar e revisar os materiais posteriormente.

## Execução

A aplicação é executada com **Docker Compose**, que sobe quatro serviços: o
banco vetorial **Qdrant**, a **LLM (Ollama)**, o **backend** (Flask, na porta
`5000`) e o **frontend** (Vite, na porta `5173`).

Por default o Ollama roda em **CPU**, então funciona em qualquer máquina. Se
tiver **GPU NVIDIA**, dá para **AUMENTAR BASTANTE A VELOCIDADE DE RESPOSTA DA LLM**.
Os modelos ficam num volume persistente (`ollama_data`), então só são baixados
uma vez.

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/)

```bash
# 1. Clone o repositório
git clone https://github.com/lewislf/studex.git
cd studex

# Escolha entre rodar com GPU ou CPU.
# 2. Suba a aplicação (GPU)
# bash scripts/setup-gpu
# docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build

# 2. Suba a aplicação (CPU)
docker compose up --build

# 3. Baixe os modelos (só na primeira vez)
docker compose exec ollama ollama pull bge-m3     # embeddings
docker compose exec ollama ollama pull llama3.2   # geração (LLM)
```

Após subir:

- Frontend: http://localhost:5173
- Backend (API): http://localhost:5000
- Qdrant: http://localhost:6333

Para rodar em segundo plano use `docker compose up --build -d` e, para encerrar,
`docker compose down` (use `docker compose down -v` só se quiser apagar também os
modelos e dados persistidos).


### Variáveis de ambiente relevantes (backend)

| Variável            | Padrão                  | Descrição                                  |
| ------------------- | ----------------------- | ------------------------------------------ |
| `OLLAMA_HOST`       | `http://ollama:11434`   | Endereço do servidor Ollama                |
| `OLLAMA_EMBED_HOST` | valor de `OLLAMA_HOST`  | Host do modelo de embeddings (se separado) |
| `OLLAMA_LLM_HOST`   | valor de `OLLAMA_HOST`  | Host do modelo de geração (se separado)    |
| `LLM_MODEL`         | `llama3.2:latest`       | Modelo de geração usado pela LLM           |
| `QDRANT_URL`        | `http://qdrant:6333`    | URL do banco vetorial Qdrant               |

### Rodar o Ollama no host em vez do container (opcional)

Para usar o Ollama instalado direto no host (reaproveitando modelos já
baixados), remova o serviço `ollama` e o `depends_on: ollama` do backend no
`docker-compose.yml`, e suba apontando a variável para o host:

```bash
OLLAMA_HOST=http://host.docker.internal:11434 docker compose up --build
```

## Documentação do Código

A documentação do projeto será gerada automaticamente através das ferramentas JSDoc (front-end) e MkDocs (back-end).

### Pré-requisito
Verifica se miniconda está instalado, cria conda env 'studex' e instala dependências.

```bash
# A partir da raiz do repositório "studex/"
bash scripts/install
```

### Como gerar documentação para o front-end

```bash
# A partir da raiz do repositório "studex/"
cd frontend
npm run docs
# Abra a documentação no navegador de sua preferência (Chrome, Firefox, Brave, etc.)
firefox docs/index.html
```

### Como gerar documentação para o back-end

```bash
# Lembre-se de ativar o Conda
conda init
source ~/.bashrc

# A partir da raiz do repositório "studex/"
cd backend
# Você pode gerar os arquivos estáticos na pasta site/ (Lembre-se de ativar o ambiente virtual)
mkdocs build
# Ou Servir localmente com hot-reload (abre em http://127.0.0.1:8000)
mkdocs serve

# Ou com Docker
docker compose up docs
```

A documentação gerada pelo MkDocs (com o plugin `mkdocstrings`) é derivada das
docstrings do código Python, de forma análoga ao JSDoc.

<p>
  <img width="180" height="120" src="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fmiro.medium.com%2Fv2%2Fresize%3Afit%3A1200%2F1*lnghcjKEV-lAxd0x6nQKuQ.png&f=1&nofb=1&ipt=0ee4ca086838cfa31038a2e44bc550520c6ad300fb79e8ac52c43404dd49c79e" /> 
  <img width="180" height="120" src="https://github.com/user-attachments/assets/bb1c48e4-44df-44cb-93a1-5b8ce9ea4d14" />
</p>

## Testes

Testes unitários utilizando PyTest para o Backend e Vitest para o Front-end

```bash
# Rodar testes unitários do Backend dentro do container (com a stack no ar)
docker compose exec backend python -m pytest

# Rodar testes unitários do Frontend dentro do container (com a stack no ar)
docker compose exec frontend npm run test
```

## Tecnologias Utilizadas

### DevOps e Ferramentas

- Git
- GitHub
- Miniconda
- npm

### Back-End

- Flask
- PostgreSQL
- PyMuPDF
- RAG (Retrieval Augmented Generation)
  - Busca híbrida (Vetorial + BM25)
  - RRF (Reciprocal Rank Fusion)
  - Cohere Rerank 3
  - text-embedding-3-small
- Gemini API
- Ollama
  - Qwen
  - Llama 3.2
  - Phi-3.5 Mini
- PyTest

### Front-End

- React
- React Router
- Vite
- Mantine
- Tabler Icons
- Vitest

## Diagrama de Classes

<img width="3158" height="2197" alt="StudexUML" src="https://github.com/user-attachments/assets/88448d27-da89-47ee-973a-1a679b314d76" />


## Telas

<img width="498" height="528" alt="home" src="https://github.com/user-attachments/assets/b66533b7-4412-4fcd-aeb5-357d7cfe1ffb" />
<img width="498" height="528" alt="revisao" src="https://github.com/user-attachments/assets/bccf13e4-31ea-4f03-98e6-d30d78969ff1" />

<img width="498" height="528" alt="estatisticas" src="https://github.com/user-attachments/assets/90c1a1a8-d99d-4b87-be4f-282f4a830789" />
<img width="498" height="528" alt="image" src="https://github.com/user-attachments/assets/3d926f02-3322-4dbb-aac0-b05ab387c648" />

## Contribuidores

<a href="https://github.com/Artur-SLO"> <img src="https://github.com/Artur-SLO.png" width="100" alt="Artur" /> </a>
<a href="https://github.com/FeLiPeOLi7"> <img src="https://github.com/FeLiPeOLi7.png" width="100" alt="Felipe" /> </a>
<a href="https://github.com/lewislf"> <img src="https://github.com/lewislf.png" width="100" alt="Luis" /> </a> 

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais informações.
