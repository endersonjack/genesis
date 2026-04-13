# TODO — Módulo de Estoque (Genesis)

Arquivo de **ideias e decisões a discutir** antes de implementar. Nada aqui é escopo fechado.

---

## 1. O que discutir primeiro (checklist)

- [x] **Cadastros-base primeiro** (ver **§2**): **FORNECEDOR** (tipos PJ, PF, Terceirizado, Terceiros, Outro), **Categoria de itens** e **Categoria de ferramentas** — fechar modelo e telas antes de movimentação complexa.
- [ ] **Escopo da fase 1**: só cadastros e movimentação básica, ou já requisições + guarda na mesma entrega?
- [x] **Multi-empresa**: **cada empresa tem o seu próprio estoque** (cadastro de itens, depósitos e saldos isolados por empresa — não compartilhar posição entre empresas).
- [ ] **Transferência entre depósitos (usuário multi-empresa)**: usuários vinculados a **mais de uma empresa** podem registrar **transferência entre depósitos**, inclusive **origem e destino em empresas diferentes**, desde que tenham permissão nas duas. Ainda definir: perfil mínimo, obrigatoriedade de observação/anexo, aprovação em duas etapas e trilha de auditoria específica.
- [ ] **Multi-filial** (dentro da mesma empresa): quantos depósitos por filial, regras de transferência interna vs. interestadual, etc.
- [ ] **Unidades de medida**: peça, kg, litro, metro, caixa; conversão entre unidades (ex.: caixa → unidade)?
- [ ] **Lotes e validade**: necessário para insumos (químico, alimento) ou pode ficar para fase 2?
- [ ] **Custo**: custo médio, FIFO, ou só quantidade sem valor contábil no primeiro momento?
- [ ] **Integração**: precisa amarrar com compras, financeiro, manutenção ou RH (EPI)?
- [ ] **Perfis e permissões**: quem aprova requisição, quem dá baixa, quem cadastra ferramenta, quem confirma devolução?
- [ ] **Auditoria**: tudo que já existe no Genesis (trilha de alterações) deve cobrir movimentos de estoque?
- [ ] **Mobile / campo**: conferência e requisição no celular (mesmo padrão do apontamento)?
- [ ] **Relatórios mínimos**: posição de estoque, consumo por período, ferramentas em poder de quem, requisições pendentes?

---

## 2. Cadastros-base — organizar primeiro

Antes de requisições, custódia e relatórios avançados, alinhar **cadastros mestres** que sustentam o catálogo e as entradas.

### 2.1 Fornecedor

- Cadastro de **Fornecedor** com **tipo** (classificação negocial), por exemplo:
  - **PJ** (pessoa jurídica)
  - **PF** (pessoa física)
  - **Terceirizado**
  - **Terceiros** (definir com o negócio a diferença em relação a *Terceirizado* — contrato, obra, nota, uso em campo?)
  - **Outro** (casos excepcionais; evitar abuso com regra de uso ou aprovação)
- Campos a fechar: razão social / nome, CNPJ/CPF e demais documentos conforme tipo, contatos, status ativo, observações.
- **Escopo por empresa**: fornecedor exclusivo da empresa no Genesis ou cadastro compartilhado com vínculo por empresa (decidir — impacta transferências e compras).
- **Uso no estoque**: principalmente **entradas** (nota, pedido, devolução de fornecedor); base para integração futura com compras/financeiro.

### 2.2 Categoria de itens

- Taxonomia para **itens / insumos** de estoque (ex.: elétrica, hidráulica, EPI, consumíveis).
- Definir: **lista plana** vs. **hierarquia** (categoria pai/filho); código curto; se categoria é **obrigatória** no cadastro do item.
- Relatórios e filtros (posição, consumo, requisição) devem usar essa categoria de forma consistente.

### 2.3 Categoria de ferramentas

- Taxonomia **específica para ferramentas** (ex.: elétrica portátil, manual, medição, fixação), para agrupar custódia, manutenção e relatórios.
- **Modelagem a decidir**:
  - **Duas entidades**: `CategoriaItem` e `CategoriaFerramenta` — simples de entender; pode haver nomes parecidos nas duas listas.
  - **Uma entidade** `Categoria` com campo **escopo** (*somente item*, *somente ferramenta*, *ambos*) — menos duplicação; telas filtram por escopo.

### 2.4 Ordem sugerida de discussão

1. Tipos de fornecedor + documentos obrigatórios por tipo + diferença Terceirizado vs. Terceiros.
2. Categorias: duas tabelas vs. uma com escopo; hierarquia sim/não.
3. Como o cadastro de **Item** referencia categoria(s) quando o item é classificado como ferramenta (só categoria de ferramentas, ou item + ferramenta?).

---

## 3. Visão sugerida: um núcleo comum + “tipos” de item

Em vez de três sistemas isolados (itens, insumos, ferramentas), costuma funcionar melhor:

1. **Catálogo único (`Item` ou `Produto`)** com campos comuns: código, nome, unidade, ativo; **sempre vinculado a uma empresa** (o mesmo código pode existir em outra empresa com outro cadastro, se a política permitir duplicidade cross-empresa); **categorias** conforme **§2** (itens vs. ferramentas).
2. **Classificação / tipo**: *item de estoque*, *insumo*, *ferramenta* (e talvez *equipamento patrimonial* se guarda for diferente de “ferramenta de uso”).
3. **Atributos por tipo** (tabelas ou JSON estruturado): ex. insumo com lote/validade; ferramenta com número de série, vida útil, calibração.

**Vantagens**: uma única tela de movimentação, um único conceito de “saldo”, requisições que misturam tipos se precisar.

**Quando separar de verdade**: se processos forem muito diferentes (ex.: patrimônio contábil com depreciação) — aí pode ser módulo à parte mas ainda compartilhando cadastro base se fizer sentido.

---

## 4. Estoque: depósitos, saldo e movimentos

- **Depósito / local**: toda movimentação amarrada a um local (almoxarifado central, obra X, veículo, etc.); **cada depósito pertence a uma empresa** (saldo nunca “mistura” empresas no mesmo depósito).
- **Saldo**: por item + depósito (+ opcional lote), respeitando a empresa do depósito e do item.
- **Movimentos** (entrada/saída/transferência/ajuste) sempre geram registro imutável ou log; saldo deriva dos movimentos ou é atualizado com trava transacional.

### Transferência entre depósitos e usuário multi-empresa

- **Transferência na mesma empresa**: depósito A → depósito B; item deve existir (ou ser mapeável) na empresa.
- **Transferência entre empresas** (caso de uso explícito): permitida para quem tem vínculo e permissão nas **duas** empresas. Na prática gera **saída** no depósito de origem (empresa X) e **entrada** no depósito de destino (empresa Y), amarradas ao mesmo documento de transferência — para auditoria e para não quebrar o isolamento de saldo por empresa.
- **Validação**: ao escolher origem/destino, o sistema só lista depósitos das empresas às quais o usuário tem acesso; operações que cruzam empresa exigem confirmação explícita (e, se definido, permissão ou perfil dedicado).
- **Catálogo em transferência cross-empresa**: decidir se o item precisa existir cadastrado nas duas empresas com o mesmo “código lógico” ou se há **cadastro espelho / vínculo** entre itens de empresas do mesmo grupo.

Tipos de movimento típicos:

- Entrada (compra, devolução, produção, ajuste positivo)
- Saída (consumo, perda, ajuste negativo)
- **Transferência entre depósitos** (mesma empresa ou, quando permitido, entre empresas para usuário multi-empresa)
- **Reserva** (opcional): bloquear quantidade para uma requisição aprovada antes da baixa física

---

## 5. Requisições (fluxo operacional)

Fluxo sugerido para discutir:

1. Solicitante abre **requisição** (itens, quantidades, obra/centro de custo, data necessária).
2. **Aprovação** (um ou mais níveis, conforme política).
3. **Separação / picking** no almoxarifado (pode parcial).
4. **Baixa no estoque** na entrega (ou na aprovação, se política for “reserva” — decidir).
5. **Devolução parcial** de não consumido (opcional).

Campos úteis: prioridade, anexo (foto/OS), vínculo com ordem de serviço ou projeto se existir no Genesis.

---

## 6. Guarda de equipamentos e ferramentas (custódia)

Diferente de “consumo” de insumo: o bem **volta** (ou deveria voltar).

Conceitos:

- **Movimento de custódia**: entrega para colaborador/terceiro com data, condição, assinatura ou confirmação.
- **Devolução**: encerra ou renova a custódia; conferência de estado (bom, com defeito, perda).
- **Ferramenta** pode ter: patrimônio, série, kit (conjunto de peças), obrigatoriedade de EPI vinculado.

Relatórios importantes: *quem está com o quê*, atrasados, histórico por ferramenta, perdas.

---

## 7. Sugestão de fases (para alinhar com o time)

| Fase | Conteúdo |
|------|-----------|
| **A** | **Fornecedor** (com tipos), **categoria de itens**, **categoria de ferramentas**; depois cadastro de itens (tipos), depósitos, movimentos manuais, saldo e consulta |
| **B** | Requisições com aprovação e baixa na entrega |
| **C** | Custódia de ferramentas/equipamentos + devolução e status |
| **D** | Lotes/validade, custo, integrações, reservas avançadas |

(Ajustar ordem conforme prioridade do negócio.)

---

## 8. Questões técnicas no Django / Genesis

- Apps sugeridos (nomes provisórios): `estoque` (núcleo), ou subdividir `estoque`, `estoque_requisicoes`, `estoque_custodia` se quiser deploy incremental.
- Modelos (cadastros-base): `Fornecedor` (FK empresa se isolado; campo **tipo**: PJ, PF, Terceirizado, Terceiros, Outro — `TextChoices`), `CategoriaItem`, `CategoriaFerramenta` *ou* `Categoria` + `escopo`.
- Modelos (núcleo): `Item` (FK empresa, FK categoria(s), FK fornecedor padrão opcional), `Deposito` (FK empresa), `MovimentoEstoque`, `TransferenciaEstoque` (opcional: agrupa par saída+entrada em cross-empresa), `ItemRequisicao`, `Requisicao`, `Custodia` / `MovimentoCustodia`.
- **Regra de autorização**: filtrar depósitos e movimentos por `request.user` + empresas associadas; transferência cross-empresa validar acesso às duas empresas no mesmo request.
- Índices: `(item_id, deposito_id)`, `(requisicao, status)`, `(custodia, devolvido_em NULL)` para listagens rápidas.
- Concurrency: `select_for_update` ao atualizar saldo em operações concorrentes.

---

## 9. Próximo passo após esta conversa

Fechar um **documento curto de decisão** (mesmo que seja um bullet list neste arquivo): **§2 completo** (fornecedor + categorias), fase 1, multi-depósito sim/não, tipos de item na v1, se custódia entra na mesma sprint que requisições, e **como tratar cadastro de item em transferência entre empresas** (dois cadastros vs. vínculo).

---

*Última atualização: cadastros-base (fornecedor, categorias) e renumeração das seções.*
