# Azure DevOps - Cadastro Rápido & Dashboards

Aplicativo Desktop moderno desenvolvido em Python com interface nativa em **CustomTkinter** (tema escuro estilo Azure DevOps), voltado para acelerar o fluxo de **cadastro**, **gestão**, **edição** e **visualização em tempo real** de demandas e Work Items (Spikes, Bugs, Tasks, User Stories) no Azure DevOps.

---

## 🚀 Principais Funcionalidades

### ➕ 1. Cadastro Rápido de Demandas
- **Padrão Suporte Automático**: Preencha apenas *Cliente*, *Módulo* e *Erro*. A descrição é padronizada e formatada automaticamente em HTML div para o Azure DevOps.
- **Geração Automática do Título**: Conforme o erro é digitado, o título da demanda é sugerido automaticamente com base na primeira frase.
- **Colar Print com `Ctrl + V`**: Tire um print na tela (`Win + Shift + S`) e pressione `Ctrl + V` no programa. A imagem é capturada diretamente da área de transferência e anexada ao card.
- **Seleção Rápida de Tags**: Tags comuns (`Cr - Cadastro Rapido`, `DemandasSistemaSuporte`, etc.) pré-configuradas em menu seletor rápido.
- **Link Imediato**: Ao cadastrar, você visualiza o link da demanda com opção de 1 clique para copiar (`📋 Copiar Link`) ou abrir direto no navegador (`🌐 Abrir no DevOps`).

### 📊 2. Dashboards Integradas em Tempo Real
- **Visualização por Dashboards do Projeto**:
  - `📋 Equipe de Desenvolvimento - Overview` *(Padrão)*: Exibe os blocos da equipe de dev (`DE - Demandas Erros`, `AES`, `PLib`, `RR`, `TVali`, `Dm`, `PClis`, `Sug`, `Cr`, `Feitos`).
  - `🎧 Dashboard - Equipe de Suporte`: Blocos específicos de suporte (`Demandas Sistema Suporte`, `Erros Sistema Suporte`, `Demandas Mobilidade Suporte`, etc.).
  - `⚙️ Dashboard - Acompanhamento Geral & Sprint`: Fila geral (`Em execução`, `Pendentes de Publicação`, `Próximas Tarefas`, `Tarefas não avaliadas`, `Bugs resolvidos`, `Concluídos`).
  - `📊 Todos os Blocos (Visão Completa)`: Carregamento de todos os blocos do projeto em paralelo.
- **Informações ao Vivo**: Ícones coloridos por tipo de item, indicador de estado com bolinha colorida (`🔵 In Progress`, `⚪ New / To Do`, `🟢 Done`), responsável atribuído e contador de itens.

### ✏️ 3. Edição Completa de Demandas
- Abra o editor clicando em qualquer card na Dashboard, digitando o número no topo (`✏️ Editar #ID`) ou através da aba de histórico.
- Permite alterar:
  - **Título** e **Descrição**.
  - **State (Status)** (`New`, `To Do`, `In Progress`, `Committed`, `Validation`, `Done`, `Removed`).
  - **Assigned To** (atribuir/alterar o desenvolvedor responsável).
  - **Tags** (com menu facilitador para mover o card entre blocos da dashboard).
  - **Urgency** e **Reported By**.
  - **💬 Comentários (Discussion)** enviados diretamente para a discussão do item.
  - **📎 Novos Anexos / Prints** enviados direto na edição.

### 🕒 4. Histórico Local
- Lista as últimas demandas cadastradas pela ferramenta com links rápidos e atalhos para abrir ou editar.

### 🔄 5. Verificação de Versão & Atualizações
- Sistema integrado para checagem de atualizações diretamente no GitHub via botão ou automático na inicialização.

---

## 🛠️ Pré-requisitos

- **Python 3.10 ou superior** instalado no Windows, Linux ou macOS.
- **Personal Access Token (PAT)** do Azure DevOps com permissão de:
  - `Work Items`: **Read, write, & manage**

---

## 📦 Instalação

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   cd SEU_REPOSITORIO
   ```

2. **Crie e ative um ambiente virtual (recomendado):**
   ```bash
   python -m venv venv
   # No Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # No Windows (CMD):
   .\venv\Scripts\activate.bat
   ```

3. **Instale as dependências:**
   ```bash
   python -m pip install -r requirements.txt
   ```

---

## ⚙️ Configuração Inicial

1. Copie o arquivo de exemplo de configuração:
   ```bash
   cp config.example.json config.json
   ```
   *(No Windows CMD/PowerShell: `copy config.example.json config.json`)*

2. Inicie o aplicativo:
   ```bash
   python app.py
   # Ou no Windows dando dois cliques em Iniciar_DevOps_Demandas.bat
   ```

3. Acesse a aba **`⚙️ Configurações`**:
   - Insira o nome da sua **Organização** no Azure DevOps.
   - Cole o seu **Personal Access Token (PAT)**.
   - (Opcional) Digite seu repositório no GitHub (`usuario/repo`) para habilitar a checagem automática de novas versões.
   - Clique em **🔌 Testar Conexão e Carregar Projetos** e em **💾 Salvar Configurações**.

---

## ⌨️ Atalhos Úteis

| Atalho | Ação |
| :--- | :--- |
| **`Ctrl + V`** | Cola print da área de transferência como anexo |
| **`Ctrl + Enter`** | Cadastra a demanda no Azure DevOps |
| **`Enter` no campo #ID** | Abre a tela de edição do número informado |
| **`Esc`** | Fecha modais de sucesso ou edição |

---

## 📁 Estrutura do Projeto

```text
├── DevOpsDemandas.exe          # Aplicativo Executável independente (pronto para uso)
├── .gitignore                  # Proteção de credenciais locais (config.json e history.json)
├── README.md                   # Documentação do projeto
└── src/                        # Código-fonte do projeto
    ├── app.py                  # Interface gráfica (CustomTkinter) e lógica de eventos
    ├── devops_api.py           # Integração REST API Azure DevOps v7.1 (Work Items, Queries, WIQL)
    ├── check_dependencies.py   # Verificador visual e instalador automático de dependências
    ├── Iniciar_DevOps_Demandas.bat # Executável/script rápido para inicialização em Python
    ├── config.example.json     # Modelo de configuração sem credenciais privadas
    └── requirements.txt        # Dependências Python necessárias
```

---

## 🔒 Segurança

> ⚠️ **IMPORTANTE:** Nunca commite o seu arquivo `config.json` ou `history.json` no GitHub. O `.gitignore` deste projeto já está pré-configurado para ignorá-los e proteger o seu Token PAT.

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais informações.
