---
exported: 2026-05-14T19:57:14.917Z
source: NotebookLM
type: note
title: "Enterprise Analytics and Political Modeling Glossary"
---

# Enterprise Analytics and Political Modeling Glossary

导出时间: 14/05/2026, 21:57:14

---

Here is a complete glossary of the unusual and specific terminology used in this project, split into technical terms and domain/operational terms.

### Tech Terms (Data Science, Operations Research, Engineering, and Statistics)

**MILP (Mixed-Integer Linear Program)**: A mathematical optimization solver (using PuLP/CBC) that finds the ideal budget allocation to maximize persuasive contacts, subject to hard feasibility constraints like reach caps, bundle binaries, and currency bands\[1\]\[2\].

**Shadow price / Dual**: The MILP solver's implicit valuation of relaxing a given constraint by exactly one unit. For instance, it provides mathematical proof of how much additional persuasion value would be generated if a specific media reach cap were expanded by 1%\[1\]\[3\].

**Participation propensity**: An entity's estimated probability of showing up and taking action on the outcome event day, measured on a scale from 0.0 to 1.0. This score is used as an allocation weight for the optimizer\[1\]\[4\].

**Platt scaling**: A post-hoc calibration technique applied to the logistic regression model to linearize the sigmoid curve, ensuring the propensity probabilities match real-world distributions rather than just acting as relative ranks\[5\].

**Department rake multiplier**: A multiplicative correction factor applied to the raw logit scores before the sigmoid transformation. It forces the synthetic population's average participation predictions to perfectly match verified regional anchors\[5\]\[6\].

**IPF / Raking (Iterative Proportional Fitting)**: A demographic calibration method that uses seeded random bit-flipping and categorical draws to force synthetic marginal distributions (like rural-urban split or language spoken) to perfectly match verified census data\[7\]\[8\].

**DBSCAN noise pre-pass**: An algorithmic step applied before K-Means segmentation. It identifies and filters out "structural noise" entities (outliers with highly unusual feature combinations) so that they do not distort the placement of the segment cluster centroids\[8\]\[9\].

**Posterior / Posterior track**: A probability distribution representing the likely values of an unknown quantity (such as the true outcome margin). It is calculated by a Bayesian hierarchical tracking model in PyMC, which updates prior beliefs as noisy survey data arrives\[1\].

**Herding effect / Measurement clustering**: A formal statistical modeling term used to replace the concept of a "bandwagon effect." It refers to the tendency of survey measurement firms to systematically cluster their published results together\[10\]\[11\].

**Phi\_transparency (φ)**: A computed observation noise multiplier between 0.10 and 1.0. It weights how much trust the Bayesian model should place in a survey record based on methodological disclosure pillars, such as sample size, field window, mode, and technical sheet (ficha) presence\[12\].

**Schema contracts**: Versioned YAML files (enforced by the Pandera library) that define the strict structural rules, data types, nullability, and expected ranges that any dataset must pass before it is handed off from one module to the next\[4\].

### Other Terms (Domain, Operations, and Narrative Replacements)

Because this repository reconstructs a political campaign but frames it for enterprise decision-analytics hiring, much of the domain vocabulary uses specific, obfuscated "clean" replacements for standard electoral terms.

**Entity**: A single synthetic individual in the target dataset. This is the project's strict replacement for the word "voter"\[1\]\[17\].

**Population dataset**: The full, synthetic roster of entities (calibrated to real demographics). This replaces the term "voter file" or "electoral roll"\[1\]\[17\].

**Outcome event**: The final, hard-deadline measurement that forecasting models target. This completely replaces words like "election" or "election day"\[1\].

**Preference proxy**: A continuous or categorical metric tracking the percentage-point lead of Candidate A over Candidate B. This replaces the term "party affinity"\[1\]\[17\].

**Survey measurement / Measurement firm**: A single data wave and the organization that collected it. These replace the terms "poll" and "pollster"\[1\].

**Exit measurement**: A specialized data collection wave occurring right before the outcome event, replacing the terms "exit poll" or "boca de urna"\[11\]\[17\].

**Program sponsor / Focal entity**: The central actor of the initiative, replacing the word "candidate" or "principal entity"\[11\]\[17\].

**Engagement activation**: The operational effort to get entities to take action on the final day. This replaces the terms "mobilization" and "GOTV" (Get Out The Vote)\[11\]\[17\].

**Conversion uplift / Response rate improvement**: The expected value of advertising and outreach. This replaces the terms "persuasion" or "behavioral outcome lift"\[17\].

**Structurally dependent**: An operational segment descriptor replacing the political concept of "clientelism" or "clientelistic dependency"\[17\]\[18\].

**Local administrative node / Local network node**: Geographic and operational network descriptors replacing the Paraguayan political terms "seccional" and "seccionalero"\[17\].

**Coordinated logistics operation**: An operational replacement term for "corralones" (a localized resource-staging tactic)\[17\].

**Preliminary transmission**: A term referring to early data reporting, replacing the specific acronym "TREP" (Transmisión de Resultados Electorales Preliminares)\[11\]\[17\].

**House effect**: The systematic bias of a specific survey measurement firm—quantifying how much they structurally overstate or understate the preference proxy for one side\[1\]\[19\].

**Reach channel**: Any communication medium used to contact entities, such as TV, radio, direct mail, or WhatsApp\[1\].

**Calibration series**: The specific baseline scenario used to anchor the mathematical models (e.g., Series A maps to the 2018 general outcome, while Series B represents an alternative)\[1\].

**NBI stress prior**: A socioeconomic metric referencing "Unmet Basic Needs" (Necesidades Básicas Insatisfechas). It is used as a structural deprivation index to assign socioeconomic stress and dependency flags to geographic regions\[4\]\[20\].

**Jopará**: A census bucket referring to a specific bilingual mix of Spanish and Guaraní, heavily used as an interaction feature to segment the Paraguayan population correctly\[4\].
---

## 引用来源

[1] business_case.md
[2] case_study_technical.pdf
[3] SPECIFICATION.md
[4] data_dictionary.md
[5] case_study_technical.md
[6] data_dictionary.md
[7] case_study_technical.md
[8] scope_master_reconstruction_project.md
[9] case_study_technical.pdf
[10] scope_module_C_forecasting_and_scenario_engine.md
[11] scope_module_C_forecasting_and_scenario_engine.md
[12] GRAPH_REPORT.md
[17] scope_master_reconstruction_project.md
[18] scope_module_A_population_modeling_and_segmentation.md
[19] post_mortem.md
[20] eda_report.md
