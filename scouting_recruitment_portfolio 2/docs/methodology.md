# Methodology: Public-Data Recruitment Decision Support MVP

## Research framing

This project demonstrates how public football data can be structured into an explainable recruitment decision-support workflow. It generates squad-need hypotheses, role-based longlists, shortlist rankings and validation flags, while clearly separating data-supported evidence from areas requiring scout, medical, tactical and financial judgement.

## Stage 0 — Club scenario

The club scenario defines assumptions that would normally come from internal recruitment leadership: preferred systems, budget ceiling, age band, target roles and scoring weights. In this MVP, those assumptions are stored in YAML so that the same pipeline can be reused for different club profiles.

## Stage 1 — Squad need hypothesis

The MVP does not claim to know the club's internal recruitment plan. Instead, it produces a **public-data need hypothesis** using:

- squad depth by role family;
- reliable depth based on minutes threshold;
- minutes dependency using a Herfindahl-style concentration measure;
- age risk;
- public availability history flag;
- performance gap against role peers.

This is aligned with the idea of squad profiles, depth charts and gap analysis in FIFA Training Centre's Talent Identification Guide Module 2.

## Stage 2 — Role taxonomy

The MVP uses broad role families from aggregate stats: CB, RWB/LWB, ST, wide player, CM, DM and AM. It avoids overclaiming fine spatial roles from aggregate data.

A future Tier B extension should use event data to capture where actions happen, enabling more spatially grounded role profiles. Player Vectors and SoccerMix are good academic directions for that extension.

A future Tier C extension could integrate broadcast-video tracking or single-camera tracking outputs. That should be framed as exploratory validation unless benchmarked against professional tracking data.

## Stage 3 — Longlist

The longlist applies transparent hard filters:

- role family;
- age range;
- minimum minutes;
- market-value proxy ceiling;
- current-club exclusion;
- optional availability and work-permit filters.

The purpose is not to find the final answer, but to create a defensible candidate universe.

## Stage 4 — Shortlist scoring

The MVP score combines five components:

```text
Final Score =
  role weight × role performance
+ complementarity weight × squad complementarity
+ value weight × value intelligence
+ reliability weight × reliability
- league risk weight × league translation risk
```

The weighting is configurable by role. This makes the model explainable and suitable for recruitment conversations.

## Role performance

Role performance is calculated within role family using robust z-scores across role-relevant metrics. Metrics are signed, so lower-is-better metrics such as errors or miscontrols can reduce the role score.

## Reliability

Per-90 outputs can overrate low-minute players. The MVP therefore shrinks role performance toward the peer average when minutes are low.

## Value intelligence

If sufficient rows are available, the MVP trains an out-of-fold Gradient Boosting model to predict log market value from public performance, age, minutes, league and role features. A positive residual means the modelled value is higher than the observed public market-value proxy.

If the dataset is too small, the pipeline falls back to a transparent value-for-money proxy: reliable role performance minus cost pressure.

## QA report

The final player card flags public-data risks such as:

- limited minutes;
- availability history;
- league step-up risk;
- missing metric coverage;
- near-budget ceiling.

These are not final judgements. They are prompts for scout, video, medical and financial validation.

## Validation plan for the next version

The next version should include:

1. Historical backtest: use season N data to rank candidates and measure outcomes in N+1 or N+2.
2. Sensitivity analysis: re-rank under alternative weights and check whether top candidates remain stable.
3. Event-data role validation: use StatsBomb Open Data and socceraction/SPADL to demonstrate xT/VAEP or spatial player profiles.
4. Video validation checklist: use data to direct which clips a scout should review.

## Source hierarchy

Academic / official sources should support methodology. Vendor and practitioner sources should only be used as industry context.

Key references:

- FIFA Training Centre, Talent Identification Guide Module 2: squad profiles, depth charts and gap analysis.
- Pappalardo et al., PlayeRank: multi-dimensional and role-aware player evaluation.
- Decroos and Davis, Player Vectors: event-stream representation of playing style.
- socceraction documentation: SPADL, xT and VAEP implementation concepts.
- StatsBomb Open Data: public event data for reproducible demonstrations.

## Public-data limitations

The portfolio should always include this statement:

> This workflow is a public-data decision-support demonstration. It can structure recruitment evidence and prioritise candidates, but it cannot replace internal scouting, tactical, medical, wage, contract, legal, personality or negotiation information.
