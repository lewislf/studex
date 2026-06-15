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
* [Como gerar a Documentação do Código](#documentação-do-código)
* [Execução](#execução) 
* [Tecnologias utilizadas](#tecnologias-utilizadas) 
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

## Documentação do Código

A documentação do projeto será gerada automaticamente através das ferramentas JSDoc e PyDoc.

- Como gerar documentação para o front-end:

```bash
cd frontend
npm run docs
```

- Como gerar documentação para o back-end:

```bash
cd backend
python -m pydoc -w .
```

A documentação gerada pelo PyDoc é derivada da docstring (i.e. atributo `__doc__`).

<p>
<img width="150" height="100" src="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fmiro.medium.com%2Fv2%2Fresize%3Afit%3A1200%2F1*lnghcjKEV-lAxd0x6nQKuQ.png&f=1&nofb=1&ipt=0ee4ca086838cfa31038a2e44bc550520c6ad300fb79e8ac52c43404dd49c79e" /> 
  <img width="150" height="100" src="https://github.com/user-attachments/assets/2a02f6fb-7235-41cc-a6e2-a8405cd72fc7" />
</p>

## Execução

```bash
# Clone o repositório
git clone https://github.com/lewislf/studex.git
cd studex

# Crie o ambiente virtual
conda create -n studex python=3.11
conda activate studex

pip install -r requirements.txt

# Rodar o Backend
cd backend/src
python3 main.py

# Rodar o frontend
cd frontend/src
npm install
npm run dev
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
- Vite
- Mantine
- Material UI
- Lucide Icons
- Vitest

## Telas

<img width="498" height="528" alt="home" src="https://github.com/user-attachments/assets/b66533b7-4412-4fcd-aeb5-357d7cfe1ffb" />
<img width="498" height="528" alt="revisao" src="https://github.com/user-attachments/assets/bccf13e4-31ea-4f03-98e6-d30d78969ff1" />

<img width="498" height="528" alt="estatisticas" src="https://github.com/user-attachments/assets/90c1a1a8-d99d-4b87-be4f-282f4a830789" />
<img width="498" height="528" alt="image" src="https://github.com/user-attachments/assets/3d926f02-3322-4dbb-aac0-b05ab387c648" />

## Contribuidores

<a href="https://github.com/Artur-SLO"> <img src="https://github.com/ArturSLO.png" width="100" alt="Artur" /> </a>
<a href="https://github.com/FeLiPeOLi7"> <img src="https://github.com/FeLiPeOLi7.png" width="100" alt="Felipe" /> </a>
<a href="https://github.com/lewislf"> <img src="https://github.com/lewislf.png" width="100" alt="Luis" /> </a> 

## Licença

Este projeto está licenciado sob a licença MIT. Consulte o arquivo LICENSE para mais informações.
