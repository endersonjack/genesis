# Instruções para agentes

## Acesso ao projeto no WSL2

Projeto: distribuição `Ubuntu-24.04`, pasta `/home/endjack/genesis`, usuário `endjack`.
Caminho Windows: `\\wsl.localhost\Ubuntu-24.04\home\endjack\genesis`.

Se o terminal ou Node REPL falhar antes de executar com `helper_unknown_error: setup refresh had errors`, use `exec_command` chamando o WSL diretamente:

- `workdir`: `C:\Windows\Temp`
- `login`: `false`
- `sandbox_permissions`: `require_escalated`, com justificativa específica; respeite a revisão de aprovação.
- Comando: `wsl.exe -d Ubuntu-24.04 --exec /bin/sh -c 'cd /home/endjack/genesis && pwd && ls -la'`

Validado em 23/09/2026: arquivos listados e permissões de leitura e escrita confirmadas. É uma alternativa ao erro do sandbox, não uma correção permanente.

Use esse acesso para o trabalho necessário, com escopo mínimo. Não altere permissões do Linux nem reinicie o WSL apenas por esse erro. Não peça novamente os caminhos já registrados. A autorização para salvar este procedimento não dispensa as revisões de aprovação exigidas pelo ambiente nas operações futuras.