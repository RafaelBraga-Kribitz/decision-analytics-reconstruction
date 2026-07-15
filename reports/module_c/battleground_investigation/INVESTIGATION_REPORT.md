# Battleground Probability Ceiling — Investigation Report

Generated: 2026-07-15T11:50:00.663509+00:00

## Executive summary

### Implementation correctness (H0)

- **H0 (implementation verification):** PASS — software matches the mathematical specification; this does **not** establish model adequacy.

### Model adequacy (H1–H5)

- **Protocol traceability outcome:** A (decision-tree label only)
- **Conclusion label:** `insufficient_evidence_for_revision`

Within the limitations of the available reference data, this investigation found **no statistically robust evidence requiring a revision** of the current mapping.

This should **not** be interpreted as proof that the current mapping is optimal; only that the present investigation did not produce sufficient evidence to justify replacing it.

- **H5 verdict summary:** Internal coherence supported (forward algebra). Adequacy: insufficient evidence to reject H5; insufficient power for moderate specification departures.
- **Fixture national margin m:** 13.521 pp (data\processed\module_c\run_all\tracking_unanchored\daily_posterior_forecast.parquet)
- **Departments at P ≥ 0.985:** Asuncion, Caazapa, Misiones, Paraguari, Neembucu, Presidente Hayes, Boqueron, Alto Paraguay
- **Effective poll sample weight (n_eff):** 14.00 (raw rows=25, 2018 holdout=5)

## Part I — Model verification (H0)

Part I addresses **implementation correctness only**. A pass here means the pipeline executes the stated mathematics; it is independent of whether that specification is appropriate for out-of-sample prediction.

| check | expected | observed | pass | tolerance |
| --- | --- | --- | --- | --- |
| swing_computation | swing_j = dept_margin_pp / national_margin_pp | max_abs_diff=0.000e+00 | True | 1e-09 |
| percentage_points_vs_proportions | margins and sigma in pp scale (not [0,1] proportions) | margins_ok=True, sigma_ok=True | True | N/A |
| hdi_to_sigma_national | (hdi_hi - hdi_lo) / (2 * z_0.97) | recomputed=10.620178, fixture=10.620178 | True | 1e-06 |
| sigma_propagation | sigma_dept = sqrt(sigma_n^2 + sigma_idio^2) | max_abs_diff=0.000e+00 | True | 1e-09 |
| phi_z_implementation | win_probability_a = Phi(swing * m / sigma_dept) | max_abs_diff=0.000e+00 | True | 1e-12 |
| clipping_audit | no probability/z clipping in heatmap.py | patterns_found=none | True | N/A |
| parquet_fidelity | exported columns match recomputed specification | max_abs_diff=0.000e+00 | True | 1e-10 |

## Part II — Model validation

### Historical reference (poll vs TSJE)

Holdout design: train on 2013 poll rows, evaluate weighted predictive scores on 2018 poll margins (target = `margin_pp_poll`; predictors use 2018 swing × TSJE national margin for each year).

| model | fold | n_rows | n_eff_weight | rmse | mae | weighted_mad |
| --- | --- | --- | --- | --- | --- | --- |
| linear | train_2013 | 20 | 9.0 | 27.01638558236421 | 23.569933220456303 | 29.585684452473224 |
| linear | holdout_2018 | 5 | 5.0 | 21.977109609855237 | 18.541691516971145 | 22.104098643711833 |
| linear_intercept | train_2013 | 20 | 9.0 | 5.6376568354604855 | 4.476864255574924 | 5.772164197645122 |
| linear_intercept | holdout_2018 | 5 | 5.0 | 22.172062886091588 | 19.09209981301375 | 29.302929214856412 |
| quadratic_swing | train_2013 | 20 | 9.0 | 9.015483536343663 | 6.891687798277969 | 6.335345948137781 |
| quadratic_swing | holdout_2018 | 5 | 5.0 | 24.378833222608897 | 20.741757633749284 | 23.202001221160458 |

Bootstrap 95% CI on weighted MAD improvement (null linear minus alternative):

- linear_intercept: mean=-2.320, CI=[-20.124, 20.124]
- quadratic_swing: mean=-0.314, CI=[-22.884, 22.884]

Breusch–Pagan-style heteroskedasticity probe (|residual| vs swing): F=7.613, p=0.0031 — **exploratory only** under n_eff=14.0; not treated as confirmatory.

### Forward decomposition (H5 internal coherence)

| department | swing_2018 | m_pp | sigma_national_pp | sigma_idio_pp | sigma_dept_pp | mu_dept_pp | z | P_recomputed | P_exported | dz_dm | dz_dsigma_dept | saturated_z_gt_3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Asuncion | 5.884332376202449 | 13.52132559595325 | 10.620178398133142 | 5.69494673024284 | 12.050751323817012 | 79.56397397344259 | 6.602407753298581 | 0.9999999999797734 | 0.9999999999797734 | 0.488295892769167 | -0.5478834950522656 | True |
| Concepcion | -1.3008178826059986 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | -17.5887821317542 | -1.1554601395070974 | 0.12395102333577046 | 0.12395102333577046 | -0.08545464949478851 | 0.07590566100534256 | False |
| San Pedro | 0.22840977537425494 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | 3.088402942133846 | 0.20288650275163764 | 0.5803881279344179 | 0.5803881279344179 | 0.015004926943875889 | -0.013328226196530523 | False |
| Cordillera | -0.3215502883179561 | 13.52132559595325 | 10.620178398133142 | 15.360889861948799 | 18.67471891512949 | -4.347786143819728 | -0.23281668460869473 | 0.40795187822602164 | 0.40795187822602164 | -0.01721848075889642 | 0.012466944518242587 | False |
| Guaira | 1.9264574561334507 | 13.52132559595325 | 10.620178398133142 | 6.944836879432623 | 12.689324193592867 | 26.04825851113221 | 2.0527695654812397 | 0.979952534222362 | 0.979952534222362 | 0.15181718322762716 | -0.16177138625851567 | False |
| Caaguazu | 0.05662083056281847 | 13.52132559595325 | 10.620178398133142 | 5.69494673024284 | 12.050751323817012 | 0.7655886855531695 | 0.0635303695994511 | 0.5253279116806212 | 0.5253279116806212 | 0.0046985311572161894 | -0.005271901136478534 | False |
| Caazapa | 3.8974781145029205 | 13.52132559595325 | 10.620178398133142 | 8.101886837561427 | 13.357722842491714 | 52.69907058929595 | 3.9452136573501178 | 0.9999601355719392 | 0.9999601355719392 | 0.29177713600291283 | -0.29535076478755473 | True |
| Itapua | 0.5441929169464418 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | 7.358209617044385 | 0.4833829793867951 | 0.6855880843977227 | 0.6855880843977227 | 0.03574967379910333 | -0.03175488562049283 | False |
| Misiones | 2.7946078400559626 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | 37.786802518400314 | 2.482329008477147 | 0.9934736651935655 | 0.9934736651935655 | 0.18358621651859894 | -0.163071678354541 | False |
| Paraguari | 3.923329805811173 | 13.52132559595325 | 10.620178398133142 | 11.591341510190375 | 15.720921958143432 | 53.04861972468091 | 3.374396225992442 | 0.9996301109874854 | 0.9996301109874854 | 0.24956105095216058 | -0.21464365989327402 | True |
| Alto Parana | -0.7599663846069288 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | -10.275752928249718 | -0.6750451977331826 | 0.2498235248541419 | 0.2498235248541419 | -0.04992448358282375 | 0.044345754726145326 | False |
| Central | -0.8260282623950991 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | -11.16899708730364 | -0.7337251002359837 | 0.23155814875398129 | 0.23155814875398129 | -0.05426428755295839 | 0.04820061447847243 | False |
| Neembucu | 5.285798536643173 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | 71.47100304856558 | 4.695145720414443 | 0.9999986679163273 | 0.9999986679163273 | 0.34724004588866914 | -0.3084382811998116 | True |
| Amambay | 1.715378279848616 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | 23.194188242059347 | 1.523696170728047 | 0.9362076867597471 | 0.9362076867597471 | 0.11268837215073563 | -0.10009619636014391 | False |
| Canindeyu | 1.9467441781962007 | 13.52132559595325 | 10.620178398133142 | 10.905539325984375 | 15.222318391058753 | 26.322561885417265 | 1.7292084693799694 | 0.9581141044518724 | 0.9581141044518724 | 0.12788749572730487 | -0.11359691900779499 | False |
| Presidente Hayes | 2.365759464455768 | 13.52132559595325 | 10.620178398133142 | 5.69494673024284 | 12.050751323817012 | 31.988204000614427 | 2.654457231840241 | 0.9960281945715643 | 0.9960281945715643 | 0.19631634583481106 | -0.22027317305884422 | False |
| Boqueron | 10.490280386053946 | 13.52132559595325 | 10.620178398133142 | 5.69494673024284 | 12.050751323817012 | 141.84249669267757 | 11.770427658924564 | 1.0 | 1.0 | 0.8705084109835572 | -0.9767380757133027 | True |
| Alto Paraguay | 5.326360914741706 | 13.52132559595325 | 10.620178398133142 | 5.69494673024284 | 12.050751323817012 | 72.019460169782 | 5.976346057979247 | 0.99999999885901 | 0.99999999885901 | 0.44199409411218427 | -0.49593140687980525 | True |

### Estimand confounding (Q-C1/Q-C2)

Poll-implied vs retrodiction companion exported under scratch battleground folder; anchored national margin (~3.7 pp) reduces ceiling prevalence relative to unanchored m.

| department | P_v0.5 | P_v0.4_replay | delta_P |
| --- | --- | --- | --- |
| Paraguari | 0.9996301109874854 | 0.8900122910103156 | 0.1096178199771698 |
| Misiones | 0.9934736651935655 | 0.8839663443096328 | 0.10950732088393267 |
| Caazapa | 0.9999601355719392 | 0.89425211171016 | 0.10570802386177924 |
| Neembucu | 0.9999986679163273 | 0.8943150180581397 | 0.10568364985818757 |
| Presidente Hayes | 0.9960281945715643 | 0.8928218272271105 | 0.10320636734445388 |
| Alto Paraguay | 0.99999999885901 | 0.8973811377086256 | 0.10261886115038443 |
| Asuncion | 0.9999999999797734 | 0.8975865942117048 | 0.10241340576806857 |
| Boqueron | 1.0 | 0.8982268896381919 | 0.10177311036180814 |

### Counterfactual m sweep

| m_pp | n_depts_P_ge_0_985 |
| --- | --- |
| -5.0 | 0.0 |
| -4.509803921568627 | 0.0 |
| -4.019607843137255 | 0.0 |
| -3.5294117647058822 | 0.0 |
| -3.0392156862745097 | 0.0 |
| -2.5490196078431375 | 0.0 |
| -2.058823529411765 | 0.0 |
| -1.5686274509803924 | 0.0 |
| -1.0784313725490198 | 0.0 |
| -0.5882352941176476 | 0.0 |
| -0.09803921568627505 | 0.0 |
| 0.39215686274509753 | 0.0 |
| 0.8823529411764701 | 0.0 |
| 1.3725490196078427 | 0.0 |
| 1.8627450980392153 | 0.0 |
| 2.352941176470588 | 0.0 |
| 2.8431372549019605 | 1.0 |
| 3.333333333333332 | 1.0 |
| 3.8235294117647047 | 1.0 |
| 4.313725490196077 | 1.0 |
| 4.80392156862745 | 2.0 |
| 5.2941176470588225 | 3.0 |
| 5.784313725490195 | 3.0 |
| 6.274509803921568 | 4.0 |
| 6.76470588235294 | 4.0 |
| 7.254901960784313 | 4.0 |
| 7.745098039215685 | 5.0 |
| 8.235294117647058 | 5.0 |
| 8.72549019607843 | 6.0 |
| 9.215686274509803 | 6.0 |
| 9.705882352941176 | 6.0 |
| 10.196078431372548 | 6.0 |
| 10.686274509803921 | 6.0 |
| 11.176470588235293 | 7.0 |
| 11.666666666666664 | 7.0 |
| 12.156862745098039 | 8.0 |
| 12.64705882352941 | 8.0 |
| 13.137254901960784 | 8.0 |
| 13.627450980392155 | 8.0 |
| 14.117647058823529 | 8.0 |
| 14.6078431372549 | 9.0 |
| 15.098039215686274 | 9.0 |
| 15.588235294117645 | 9.0 |
| 16.07843137254902 | 9.0 |
| 16.56862745098039 | 9.0 |
| 17.058823529411764 | 10.0 |
| 17.549019607843135 | 10.0 |
| 18.03921568627451 | 10.0 |
| 18.52941176470588 | 10.0 |
| 19.019607843137255 | 10.0 |
| 19.509803921568626 | 11.0 |
| 20.0 | 11.0 |

## Statistical power and detectable effects

- Weighted effective sample size (all poll rows): **14.0**
- 2018 holdout rows / effective weight: **5** / **5.0**
- Bootstrap 95% CI half-width on MAD difference: **±20.1 pp**
- Approximate minimum detectable MAD improvement (holdout): **20.1 pp**

Simulation-based power (reject H5 if bootstrap 95% CI on MAD improvement excludes zero):

| true_mad_improvement_pp | power | type_ii_error |
| --- | --- | --- |
| 5.0 | 0.0 | 1.0 |
| 10.0 | 0.0 | 1.0 |
| 15.0 | 0.0 | 1.0 |
| 20.0 | 0.0 | 1.0 |
| 25.0 | 1.0 | 0.0 |

The investigation is unlikely to detect practically meaningful departures (5–10 pp weighted MAD improvement on holdout) with adequate power.

## Posterior predictive checks

Scalar PPC p-values (supplementary):

| statistic | value |
| --- | --- |
| ppc_pvalue_max_margin_2013 | 0.6336 |
| ppc_pvalue_min_margin_2013 | 0.9994 |
| ppc_pvalue_max_margin_2018 | 0.6282 |
| ppc_pvalue_min_margin_2018 | 0.8166 |
| ppc_pvalue_ceiling_count | 0.4162 |
| observed_ceiling_count | 8.0 |
| sim_ceiling_q5 | 0.0 |
| sim_mean_abs_z_q5 | 0.20094592901568684 |
| sim_max_p_q5 | 0.5637726615581344 |
| sim_ceiling_q50 | 5.0 |
| sim_mean_abs_z_q50 | 2.0824252810903854 |
| sim_max_p_q50 | 0.9999999999998612 |
| sim_ceiling_q95 | 11.0 |
| sim_mean_abs_z_q95 | 5.433803635427056 |
| sim_max_p_q95 | 1.0 |

Graphical PPC diagnostics compare observed election summaries to simulated replicates. Visual typicality is the primary PPC evidence; scalar p-values are reported but not relied upon alone.

Figures: `ppc_dept_margins_2018.png`, `ppc_dept_margins_faceted.png`, `ppc_dept_probabilities.png`, `ppc_z_distribution.png`, `ppc_ceiling_count.png`, `ppc_summary_panel.png`, plus residual/forward diagnostics in `figures/`.

## Part III — Model criticism

Evidence synthesis distinguishes **implementation verification**, **internal coherence**, and **model adequacy**. Non-rejection of H1–H4 is **not** equivalent to confirming H5.

### H5 three-way verdict

| verdict_type | assessment | interpretation |
| --- | --- | --- |
| Evidence supporting H5 (internal coherence) | supported at fixture inputs | Forward algebra matches export; ceiling follows from fixture inputs under stated assumptions. |
| Insufficient evidence to reject H5 | insufficient evidence to reject H5 on holdout predictive performance and PPC; insufficient statistical power for moderate departures | Alternatives did not outperform null on holdout with bootstrap CI excluding zero. |
| Insufficient statistical power | The investigation is unlikely to detect practically meaningful departures (5–10 pp weighted MAD improvement on holdout) with adequate power. | Approx. MDE ≈ 20.1 pp weighted MAD on holdout. |

### Hypothesis-level status

- **H0_implementation:** verified
- **H1_mean_spec:** not rejected — holdout predictive performance does not favour alternative
- **H2_variance_spec:** exploratory signal only (BP p=0.0031) — underpowered; not basis for rejection
- **H3_sigma_quantification:** not evaluated with holdout power — inconclusive
- **H4_likelihood_spec:** not evaluated with holdout power — inconclusive
- **H5_internal_coherence:** supported — recomputed z/P match export; ceiling follows from fixture inputs under stated assumptions
- **H5_adequacy:** insufficient evidence to reject H5 on holdout predictive performance and PPC; insufficient statistical power for moderate departures

## Decision protocol

Alternatives falsify H5 only with better holdout predictive performance and bootstrap CI excluding zero, or PPC failure remedied by an alternative. Failure to reject alternatives under low power is recorded as **insufficient evidence**, not confirmation of adequacy.

## Limitations

- 25 poll rows with proxy duplication; effective n is much smaller than row count.
- 2018 holdout contains only five poll rows — predictive comparisons are underpowered.
- Bootstrap CIs on holdout MAD differences are wide; moderate specification departures may not be detectable.
- Type II error rates are elevated for 5–10 pp MAD improvements (see power table).
- Swing factors fixed from realized 2018 TSJE; forward mapping is separate from historical validation.
- H0 verification establishes software fidelity only; it does not validate the specification.

## Artifacts

- Primary export used: `reports\module_c\battleground_investigation\scratch\battleground\battleground_department_probability.parquet`
- Model version: `c_battleground_v0.5`

