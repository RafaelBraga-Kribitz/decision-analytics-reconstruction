---
exported: 2026-05-14T19:54:37.713Z
source: NotebookLM
type: note
title: "The Paraguay 2018 Model: Data Integration and Validation Roadmap"
---

# The Paraguay 2018 Model: Data Integration and Validation Roadmap

导出时间: 14/05/2026, 21:54:37

---

While this project is deliberately built using synthetic data to avoid privacy and governance issues, it is anchored to real-world statistics\[1\]\[2\]. However, the system's documentation maintains an explicit "Open Evidence Gaps" registry highlighting where real-world data is currently estimated, partially implemented, or missing entirely\[3\].

Finding and integrating the following datasets would elevate the system from a methodological reconstruction to a fully verified, production-ready replica of the 2018 Paraguayan context:

**1\. Electoral and Participation Data**

**Full TSJE Departmental Tables:** The system currently relies on the exact 2018 participation rates for only four exemplar departments (Presidente Hayes, Alto Paraná, Central, and Guairá)\[4\]\[5\]. The other 14 departments are using a placeholder national mean of 61.25%\[4\]. Finding the complete departmental elector totals and participation tables from the TSJE (Paraguayan electoral authority) is marked as a "BLOCKING" gap preventing full verification of the population model\[3\]\[6\].

**Real Adherence Cohorts:** The propensity model currently trains on synthetic labels derived from these calibration anchors. Replacing these synthetic labels with a real historical voter adherence cohort would allow for true validation of the model's accuracy, rather than just testing how well it reproduces its own synthetic generation process\[1\]\[7\].

**2\. Financial and Economic Data**

**Exact BCP Exchange Rates:** The resource allocation optimizer models an exchange rate corridor constraint (5,500–5,700 PYG/USD), but the exact daily interbank reference rates (`TC_Ref`) from the Central Bank of Paraguay (BCP) for January through April 2018 are pending\[3\]\[8\].

**Retail FX Spreads:** The retail exchange spread at exchange houses (_casas de cambio_) used for field operations is currently estimated at ~+50 PYG/USD\[3\]\[8\]. Historical market data would make this cost modeling exact.

**Program and Operational Scale:** The total program budget (~$2M USD) and the logistics scale (e.g., 200 events, 5,000 field staff) are currently estimated placeholders that need to be verified against published historical reporting\[3\].

**3\. Demographic and Socioeconomic Data**

**DGEEC Household Survey Microdata:** The synthetic population generation currently uses independent conditional draws (e.g., rural status, language, age) to match marginal averages\[9\]\[10\]. Retrieving published DGEEC (census) household survey microdata would allow the creation of a Gaussian copula to enforce highly realistic joint correlations—such as accurately modeling how language, rural status, and age specifically overlap in the population\[11\].

**Granular NBI (Unmet Basic Needs) Data:** The `nbi_stress_prior` used to identify the "Structurally Dependent" behavioral segment is currently flagged as `ESTIMATED`. Exact table identifiers from the DGEEC 2012 Census are required to replace this estimate with a granular NBI mesh\[3\]\[12\].

**ICT Penetration Survey:** The exact publication year and URL for the ITU/SENATIC/ATP internet penetration survey (used to accurately model digital reachability across urban and rural zones) is still needed\[3\].

**4\. Polling and Infrastructure Data**

**Survey Methodological Sheets (****Ficha Técnica****):** Module C's probabilistic forecasting uses a "transparency penalty" to down-weight polls that lack methodological transparency. However, the original press release PDFs and technical disclosure sheets for these polls need to be recovered to properly calculate these penalties and resolve attribution conflicts for firms like Ati Snead and ProLogo\[3\]\[13\].

**Road Network Citations:** The exact MOPC (Ministry of Public Works) or World Bank Rural Access Indicator (RAI) publication verifying the road network length and unpaved road shares is pending\[3\]. This is necessary to perfect the routing cost matrix used to calculate field operations logistics\[14\].

Since the project explicitly identifies these gaps, finding this real-world historical data would resolve the remaining "estimated" flags and allow the system's models to fully process the exact 2018 electoral conditions.

Would you like me to run a deep web research search to locate the official TSJE 2018 departmental participation rates or the historical BCP exchange rate data to help fill these gaps?
---

## 引用来源

[1] HIRING_CONTEXT.md
[2] scope_master_reconstruction_project.md
[3] scope_master_reconstruction_project.md
[4] decision_log.md
[5] model_card_propensity.md
[6] ROADMAP.md
[7] scope_module_A_population_modeling_and_segmentation.md
[8] case_study_technical.md
[9] statistical_independence_note.md
[10] statistical_independence_note.md
[11] statistical_independence_note.md
[12] data_dictionary.md
[13] scope_module_C_forecasting_and_scenario_engine.md
[14] scope_module_B_resource_allocation_engine.md

---

# Bridging the Gap: Data Requirements for Paraguayan Electoral Models

导出时间: 14/05/2026, 21:55:39

---

While this project is deliberately built using synthetic data to avoid privacy and governance issues, it is anchored to real-world statistics\[1\]\[2\]. However, the system's documentation maintains an explicit "Open Evidence Gaps" registry highlighting where real-world data is currently estimated, partially implemented, or missing entirely\[3\].

Finding and integrating the following datasets would elevate the system from a methodological reconstruction to a fully verified, production-ready replica of the 2018 Paraguayan context:

**1\. Electoral and Participation Data**

**Full TSJE Departmental Tables:** The system currently relies on the exact 2018 participation rates for only four exemplar departments (Presidente Hayes, Alto Paraná, Central, and Guairá)\[4\]\[5\]. The other 14 departments are using a placeholder national mean of 61.25%\[4\]. Finding the complete departmental elector totals and participation tables from the TSJE (Paraguayan electoral authority) is marked as a "BLOCKING" gap preventing full verification of the population model\[3\]\[6\].

**Real Adherence Cohorts:** The propensity model currently trains on synthetic labels derived from these calibration anchors. Replacing these synthetic labels with a real historical voter adherence cohort would allow for true validation of the model's accuracy, rather than just testing how well it reproduces its own synthetic generation process\[1\]\[7\].

**2\. Financial and Economic Data**

**Exact BCP Exchange Rates:** The resource allocation optimizer models an exchange rate corridor constraint (5,500–5,700 PYG/USD), but the exact daily interbank reference rates (`TC_Ref`) from the Central Bank of Paraguay (BCP) for January through April 2018 are pending\[3\]\[8\].

**Retail FX Spreads:** The retail exchange spread at exchange houses (_casas de cambio_) used for field operations is currently estimated at ~+50 PYG/USD\[3\]\[8\]. Historical market data would make this cost modeling exact.

**Program and Operational Scale:** The total program budget (~$2M USD) and the logistics scale (e.g., 200 events, 5,000 field staff) are currently estimated placeholders that need to be verified against published historical reporting\[3\].

**3\. Demographic and Socioeconomic Data**

**DGEEC Household Survey Microdata:** The synthetic population generation currently uses independent conditional draws (e.g., rural status, language, age) to match marginal averages\[9\]\[10\]. Retrieving published DGEEC (census) household survey microdata would allow the creation of a Gaussian copula to enforce highly realistic joint correlations—such as accurately modeling how language, rural status, and age specifically overlap in the population\[11\].

**Granular NBI (Unmet Basic Needs) Data:** The `nbi_stress_prior` used to identify the "Structurally Dependent" behavioral segment is currently flagged as `ESTIMATED`. Exact table identifiers from the DGEEC 2012 Census are required to replace this estimate with a granular NBI mesh\[3\]\[12\].

**ICT Penetration Survey:** The exact publication year and URL for the ITU/SENATIC/ATP internet penetration survey (used to accurately model digital reachability across urban and rural zones) is still needed\[3\].

**4\. Polling and Infrastructure Data**

**Survey Methodological Sheets (****Ficha Técnica****):** Module C's probabilistic forecasting uses a "transparency penalty" to down-weight polls that lack methodological transparency. However, the original press release PDFs and technical disclosure sheets for these polls need to be recovered to properly calculate these penalties and resolve attribution conflicts for firms like Ati Snead and ProLogo\[3\]\[13\].

**Road Network Citations:** The exact MOPC (Ministry of Public Works) or World Bank Rural Access Indicator (RAI) publication verifying the road network length and unpaved road shares is pending\[3\]. This is necessary to perfect the routing cost matrix used to calculate field operations logistics\[14\].

Since the project explicitly identifies these gaps, finding this real-world historical data would resolve the remaining "estimated" flags and allow the system's models to fully process the exact 2018 electoral conditions.

Would you like me to run a deep web research search to locate the official TSJE 2018 departmental participation rates or the historical BCP exchange rate data to help fill these gaps?
---

## 引用来源

[1] HIRING_CONTEXT.md
[2] scope_master_reconstruction_project.md
[3] scope_master_reconstruction_project.md
[4] decision_log.md
[5] model_card_propensity.md
[6] ROADMAP.md
[7] scope_module_A_population_modeling_and_segmentation.md
[8] case_study_technical.md
[9] statistical_independence_note.md
[10] statistical_independence_note.md
[11] statistical_independence_note.md
[12] data_dictionary.md
[13] scope_module_C_forecasting_and_scenario_engine.md
[14] scope_module_B_resource_allocation_engine.md

---
Here are the optimized search queries for each of the open evidence gaps, formulated specifically for a deep research tool. They are detailed, specify the exact timeframe (early 2018), and include both acronyms and full organization names to yield the best results.

You can copy and paste these directly:

**1\. Electoral & Participation Data (TSJE)**`Find the official departmental voter turnout rates and total elector counts from the TSJE (Tribunal Superior de Justicia Electoral) for the April 2018 Paraguay general elections. I need the exact participation percentages broken down for all 18 specific departments, not just the national average.`

**2\. Financial Data: Central Bank Exchange Rates (BCP)**`Find the historical daily official exchange rates (Cotización de Referencia or TC_Ref) for the US Dollar (USD) to Paraguayan Guaraní (PYG) published by the Central Bank of Paraguay (Banco Central del Paraguay - BCP) strictly for the period between January 1, 2018, and April 30, 2018.`

**3\. Financial Data: Retail Exchange Spread (Casas de Cambio)**`Find historical financial data, economic bulletins, or financial news reports from Paraguay between January and April 2018 detailing the average retail exchange rate spread (the difference between the buy and sell price for USD to PYG) applied by local exchange houses (casas de cambio) compared to the BCP official interbank rate.`

**4\. Campaign Operations & Budget Scale**`Find published news reports, investigative journalism, TSJE campaign finance declarations, or EU/OEA election observer reports regarding the total campaign budget spent, the logistics scale, the number of field staff (operadores/mesarios), and the total number of campaign rallies for the ANR (Mario Abdo Benítez) 2018 presidential campaign in Paraguay.`

**5\. Polling Data & Methodological Transparency (Fichas Técnicas)**`Locate original press releases, news articles, PDF reports, or "fichas técnicas" (methodological data sheets) for Paraguay presidential election polls published in March and April 2018 by the polling firms Ati Snead, ProLogo, ICA, and CAPLI. Specifically, look for sample sizes, field dates, margin of error, and any data resolving conflicting poll numbers released by Ati Snead or ProLogo in early April 2018.`

**6\. Demographic Data: Unmet Basic Needs (NBI)**`Find the exact table identifiers and granular departmental-level statistical tables for the NBI (Necesidades Básicas Insatisfechas) index from the Paraguay 2012 National Census, published by the DGEEC (Dirección General de Estadística, Encuestas y Censos) or the INE (Instituto Nacional de Estadística).`

**7\. Infrastructure Data: Road Networks (MOPC / World Bank)**`Find official publications, datasets, or specific citations from the Paraguayan Ministry of Public Works and Communications (MOPC) or the World Bank Rural Access Indicator (RAI) from circa 2017-2018 detailing the total length of the road network and the specific percentage of paved versus unpaved (tierra/encampio) roads per department in Paraguay.`

**8\. Socioeconomic Data: ICT Penetration Survey**`Locate the official internet, media, and ICT penetration survey for Paraguay published around 2017 or 2018 by SENATICs (Secretaría Nacional de Tecnologías de la Información y Comunicación), MITIC, or the ITU. I am specifically looking for the raw survey data on rural versus urban digital reachability, internet access percentages, and WhatsApp/smartphone usage statistics by demographic.`

---

# 2018 Paraguay Data Resolution and System Calibration Updates

导出时间: 14/05/2026, 21:53:44

---

The new sources provided contain exactly the historical, macroeconomic, and institutional data needed to resolve the "Open Evidence Gaps" previously flagged as blocking or estimated in the project's documentation.

Here is how we can now fill every major missing data gap in the system:

### 1\. Electoral and Participation Data (TSJE)

Previously, the system only had exact participation anchors for four exemplar departments and used a placeholder for the rest. We now have the **definitive TSJE 2018 general election participation rates for all 18 jurisdictions**, which can perfectly calibrate the propensity model's department rake multiplier\[1\]:

**Asunción (Capital):** 67.71%
**Central:** 62.07%
**Alto Paraná:** 62.91%
**Amambay:** 68.54% (Highest national turnout)
**Alto Paraguay:** 68.30%
**Ñeembucú:** 67.40%
**Misiones:** 67.25%
**Cordillera:** 63.88%
**Paraguarí:** 61.00%
**Guairá:** 60.61%
**Concepción:** 60.28%
**Caaguazú:** 59.32%
**Canindeyú:** 59.20%
**Presidente Hayes:** 58.16%
**San Pedro:** 57.47%
**Boquerón:** 57.37%
**Itapúa:** 56.93%
**Caazapá:** 56.84% (Lowest national turnout)

### 2\. Financial and Economic Data (BCP & Retail Spreads)

We can now replace the estimated exchange rate models with the exact financial dynamics of the January–April 2018 period:

**Exact BCP Exchange Rates (TC\_Ref):** The Guaraní reached its annual minimum (peak strength) in March 2018 at exactly **5,500 PYG/USD**\[2\]\[3\]. The monthly averages were: Jan (5,600), Feb (5,560), Mar (5,540), and Apr (5,570)\[3\].

**Retail FX Spread:** The "casa de cambio" retail spread during this exact four-month window averaged **40 to 50 PYG** above the interbank rate\[4\]\[5\]. This means the system's previous ~+50 PYG/USD estimate was remarkably accurate and can now be officially tagged as verified\[6\]\[7\].

### 3\. Campaign Operations and Budget Scale

The placeholders for logistics and budget can now be updated to reflect the true scale of the ANR's 2018 operations:

**Logistics & Field Staff:** The campaign did not just use 5,000 staff. To cover the 12,000+ voting tables (mesas), the ANR deployed over **70,000 day-of field staff**, which included at least 36,000 _mesarios_ (table officials), 12,000 _veedores_ (observers), and 1,000 _apoderados_ (legal proxies), plus thousands of _operadores_\[8\].

**Budget Scale:** The 2MUSDplaceholdervastlyunderestimatesthereality.Whileofficialdeclarationswerelower,the2018primaryandgeneralcampaigncombinedwerehighlycapitalized,withsubsequentinvestigativeauditssuggestingthatapproximately∗∗44 million USD\*\* was allocated specifically for advertising _pautas_\[11\]\[12\].

### 4\. Infrastructure and Routing Data

The routing cost matrix in Module B can now be precisely calibrated with the official MOPC 2018 road inventory:

**Total Network:** 80,127 km\[13\].

**Surface Composition:** Only **8.72% (6,987 km) of the network was paved**, while **88.16% (70,643 km) consisted of unpaved earth tracks**\[14\]. An additional 3.09% were "improved" surfaces like cobblestone (_empedrados_)\[14\].

**Rural Access Index (RAI):** Officially measured at **42.4%** in 2019 using 2018 datasets, meaning over 57% of the rural population lacked reliable all-season road access\[15\].

### 5\. Polling Data and Methodological Transparency

The precise details of the "guerra de encuestas" (war of polls) are now available to feed Module C's Bayesian aggregator:

**The Early April Conflict:** On April 3, Ati Snead released a poll showing a dead heat (Alegre 44.6% vs. Abdo 42.9%)\[16\]\[17\]. Six days later, ProLogo released a poll showing a massive 28-point blowout (Abdo 50% vs. Alegre 22%)\[17\]\[18\].

**The "Establishment Benchmark":** ICA (Taka Chase) released a poll on March 18 showing a staggering 31.4-point lead for Abdo (58.2% to 26.8%), representing a massive "house effect" overstatement\[16\]\[19\].

### 6\. Demographic Data: NBI and ICT Penetration

**NBI Identifiers:** The exact DGEEC 2012 Census identifiers for structural poverty (NBI) are the housing/population tables **V01 through V08** and **P01 through P07**\[20\]. For automated retrieval, the INE Tableau Workbook LUID is `53cfb7a5-3074-40e0-9d27-7b046d0ce5a8`\[21\].

**ICT / Internet Penetration:** The exact data comes from the _Encuesta Permanente de Hogares Continua_ (EPHC)\[22\]. It shows internet penetration rose rapidly: urban access was **70.6% in 2017** and **74.1% in 2018**, while rural access was **44.0% in 2017** and **48.7% in 2018**\[23\]. Furthermore, by 2018, **96.3% of all internet users** reported using it primarily for WhatsApp/instant messaging\[24\]\[25\].

With this data, the project can completely remove its `[ESTIMATED]` tags and operate on perfectly reconstructed 2018 realities.

Would you like me to draft the specific `YAML` configuration file updates for the Module A population anchors or the Module B resource constraints using these exact figures?
---

## 引用来源

[1] Comprehensive Analysis of Electorate Distribution and Voter Participation in the 2018 Paraguayan General Elections: A Departmental Study of Institutional and Civic Engagement
[2] Macroeconomic Analysis of the Paraguayan Guaraní: Daily Exchange Rate Dynamics and the Institutional Framework of the Banco Central del Paraguay (January–April 2018)
[3] Macroeconomic Analysis of the Paraguayan Guaraní: Daily Exchange Rate Dynamics and the Institutional Framework of the Banco Central del Paraguay (January–April 2018)
[4] Paraguayan Exchange Rate Dynamics: A Comprehensive Analysis of Retail Spreads and Interbank Benchmarks (January–April 2018)
[5] Paraguayan Exchange Rate Dynamics: A Comprehensive Analysis of Retail Spreads and Interbank Benchmarks (January–April 2018)
[6] scope_module_B_resource_allocation_engine.md
[7] scope_module_B_resource_allocation_engine.md
[8] The 2018 Presidential Campaign of the Asociación Nacional Republicana: An Exhaustive Analysis of Financial Architecture, Logistical Mobilization, and Electoral Integrity
[11] The 2018 Presidential Campaign of the Asociación Nacional Republicana: An Exhaustive Analysis of Financial Architecture, Logistical Mobilization, and Electoral Integrity
[12] The 2018 Presidential Campaign of the Asociación Nacional Republicana: An Exhaustive Analysis of Financial Architecture, Logistical Mobilization, and Electoral Integrity
[13] Technical Assessment of the Paraguayan Road Infrastructure: National Inventory, Departmental Distribution, and Rural Connectivity Metrics (2017-2018)
[14] Technical Assessment of the Paraguayan Road Infrastructure: National Inventory, Departmental Distribution, and Rural Connectivity Metrics (2017-2018)
[15] Technical Assessment of the Paraguayan Road Infrastructure: National Inventory, Departmental Distribution, and Rural Connectivity Metrics (2017-2018)
[16] Psephological Divergence and the Structural Dynamics of the 2018 Paraguayan Presidential Election: A Comparative Analysis of Polling Methodologies and Outcomes
[17] Psephological Divergence and the Structural Dynamics of the 2018 Paraguayan Presidential Election: A Comparative Analysis of Polling Methodologies and Outcomes
[18] Psephological Divergence and the Structural Dynamics of the 2018 Paraguayan Presidential Election: A Comparative Analysis of Polling Methodologies and Outcomes
[19] Psephological Divergence and the Structural Dynamics of the 2018 Paraguayan Presidential Election: A Comparative Analysis of Polling Methodologies and Outcomes
[20] Socioeconomic Structural Analysis of Unsatisfied Basic Needs in Paraguay: A Comprehensive Evaluation of the 2012 National Census Data
[21] Socioeconomic Structural Analysis of Unsatisfied Basic Needs in Paraguay: A Comprehensive Evaluation of the 2012 National Census Data
[22] The Digital Architecture of Paraguay: A Multi-Dimensional Analysis of ICT Penetration and Socio-Technical Dynamics (2017-2018)
[23] The Digital Architecture of Paraguay: A Multi-Dimensional Analysis of ICT Penetration and Socio-Technical Dynamics (2017-2018)
[24] The Digital Architecture of Paraguay: A Multi-Dimensional Analysis of ICT Penetration and Socio-Technical Dynamics (2017-2018)
[25] The Digital Architecture of Paraguay: A Multi-Dimensional Analysis of ICT Penetration and Socio-Technical Dynamics (2017-2018)