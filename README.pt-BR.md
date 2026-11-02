# Reconstrução de Decision Analytics — Eleição presidencial do Paraguai de 2018

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Resumo

Este projeto reconstrói, para fins de análise decisória, a eleição presidencial paraguaia de 2018. Ele conecta três componentes: segmentação sintética de eleitores e propensão ao comparecimento, alocação de orçamento de campanha por otimização com restrições e acompanhamento bayesiano de pesquisas com cenários de Monte Carlo.

O resultado eleitoral verificado foi uma margem de **+3,70 pontos percentuais** para Mario Abdo Benítez (46,43% contra 42,73%), com comparecimento de 61,25%. O sistema usa resultados eleitorais, dados censitários e oito pesquisas publicadas como referências públicas. Os registros individuais de eleitores são **sintéticos**; os resultados de rastreamento e os cenários são **ilustrativos**.

Uma reprodução ilustrativa da semana 8 realoca US$ 766 mil de seis departamentos competitivos e estima +1,20% em contatos ponderados por persuasão, mantendo o orçamento de US$ 6,03 milhões. Isso não é uma estimativa causal: depende de uma atualização manual de pesos, e o efeito se inverte na extremidade pessimista do intervalo.

## O que o projeto demonstra

- Segmentação de eleitores e estimativa de propensão ao comparecimento.
- Otimização de orçamento por programação linear inteira mista (MILP) e roteamento de campo.
- Rastreamento bayesiano de pesquisas e análise de cenários.
- Separação explícita entre dados verificados, calibrados, simulados e ilustrativos.

## Limites essenciais

A reconstrução não afirma que a análise causou o resultado eleitoral nem que prevê eleições com precisão. Há apenas oito pesquisas, e a validação fora da amostra é limitada. Os microdados são sintéticos, e a função objetivo usa contatos ponderados como proxy, não curvas de resposta de mídia estimadas com resultados observados.

## Explorar e reproduzir

Consulte o [README completo em inglês](README.md) para resultados, arquitetura, dados, limitações, demonstrações e comandos de reprodução. O projeto usa Python 3.11, Poetry e semente fixa 42. Execute `poetry install`, `make test` e `make pipeline-full`; os serviços locais estão descritos no README principal.

[Repositório e demonstrações](https://github.com/RafaelBraga-Kribitz/decision-analytics-reconstruction) · [Estudo de caso](reports/CASE_STUDY.md) · [Limites epistemológicos](reports/epistemic_boundaries.md)
