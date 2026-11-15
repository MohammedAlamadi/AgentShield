"""B. Evaluation Results. Every number is read from the validated aggregates, the detector run or the run logs;
R1, Q1 and S1 are always shown separately (never pooled)."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import components as ui
import state
from agentshield.dashboard import data as D

AX = {"labelColor": "#C9D2E3", "titleColor": "#8A97B2", "gridColor": "#1E2A44", "domainColor": "#24314F", "tickColor": "#24314F"}


def _cfg(chart):
    return (chart.configure_view(strokeWidth=0).configure_axis(**AX).configure_legend(labelColor="#C9D2E3", titleColor="#8A97B2")
            .configure(background="transparent"))


def _pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def _range(lo, hi):
    return _pct(lo) if lo == hi else f"{_pct(lo)} – {_pct(hi)}"


def _ci(ci):
    return "" if not ci else f"[{ci[0] * 100:.1f}, {ci[1] * 100:.1f}]"


CFG_SCALE = alt.Scale(domain=[D.CONFIG_LABEL[c] for c in D.CONFIG_ORDER], range=[ui.CONFIG_COLOR[c] for c in D.CONFIG_ORDER])


def _overview():
    ov = state.overview()
    idx = state.run_index()
    E = ov["experiments"]
    n_att = len({r["scenario"] for r in idx.runs if r["is_attack"]})
    n_sc = len({r["scenario"] for r in idx.runs})
    inc = {e: v["inconclusive"] for e, v in E.items() if v["inconclusive"]}
    unres = [f"{r['experiment']} {r['scenario']}/{r['config']} rep {r['repetition']}" for r in idx.runs if r["attack"] == "manual_review"]
    c = st.columns(4)
    with c[0]:
        ui.kpi("End-to-end runs", f"{ov['total_runs']:,}", " + ".join(f"{e} {v['runs']:,}" for e, v in E.items()) + " (the 200-run reference evaluation is R1 repetition 1, counted once)")
    with c[1]:
        ui.kpi("Frozen scenarios", str(n_sc), f"{n_att} attack + {n_sc - n_att} benign; datasets and scoring frozen before any run")
    with c[2]:
        ui.kpi("Inconclusive runs", str(sum(inc.values())), ("in " + ", ".join(f"{e} ({n})" for e, n in inc.items()) if inc else "none") + " · model-call timeout; excluded from denominators", ui.C["amber"])
    with c[3]:
        ui.kpi("Unresolved reviews", str(len(unres)), ("; ".join(unres) + " · single review → reported as a range") if unres else "none", ui.C["amber"])
    st.write("")
    rows = []
    for e, v in ov["experiments"].items():
        rows.append({"Experiment": e, "Model": ", ".join(v["model"]), "Configurations": ", ".join(D.CONFIG_LABEL[x] for x in v["configs"]),
                     "Repetitions / seeds": v["repetitions"], "Runs": v["runs"], "Inconclusive": v["inconclusive"], "Six-call-limit stops": v["call_limit_stops"],
                     "Adjudicated attack items": v["adjudicated"], "Unresolved": v["manual_review_unresolved"], "Median s/run": v["median_wall_time_s"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    for e in ("R1", "Q1", "S1"):
        ui.explain(f"{e}: {D.EXPERIMENT_TEXT[e]}")
    ui.warnbox("The three experiments differ in model, sampling and repetitions. Their rates are shown side by side only; they are never combined into one percentage.")
    # side-by-side small multiples of overall attack success (bounds) per experiment
    recs = []
    for e in ("R1", "Q1", "S1"):
        for r in state.metric_table(e):
            recs.append({"Experiment": e, "Configuration": r["config_label"], "lower": r["attack_success_lower"], "upper": r["attack_success_upper"],
                         "legit": r["legit_success"]})
    df = pd.DataFrame(recs)
    base = alt.Chart(df).encode(y=alt.Y("Configuration:N", sort=[D.CONFIG_LABEL[c] for c in D.CONFIG_ORDER], title=None))
    bars = base.mark_bar(cornerRadiusEnd=4, height=14).encode(x=alt.X("upper:Q", title="Attack success rate (all attack scenarios)", axis=alt.Axis(format="%")),
                                                             color=alt.Color("Configuration:N", scale=CFG_SCALE, legend=None),
                                                             tooltip=["Experiment", "Configuration", alt.Tooltip("lower:Q", format=".1%"), alt.Tooltip("upper:Q", format=".1%")])
    lo = base.mark_tick(color="white", thickness=2, size=16).encode(x="lower:Q")
    st.altair_chart(_cfg(alt.layer(bars, lo).properties(width=270, height=170).facet(
        column=alt.Column("Experiment:N", title=None, sort=["R1", "Q1", "S1"], header=alt.Header(labelColor="#E6EAF2", labelFontSize=14))).resolve_scale(x="independent")),
                    use_container_width=False)
    st.caption("Bars = upper bound, white tick = lower bound (they differ only where a manual-review item is unresolved). Over ALL 26 attack scenarios, "
               "so a low rate partly reflects how rarely the model attempts attacks at all.")


def _experiment(exp: str):
    mt = state.metric_table(exp)
    idx = state.run_index()
    counts = D.counts_with_denominators(idx.runs, exp)
    cset = state.conditional_set(exp)
    ui.explain(D.EXPERIMENT_TEXT[exp])
    if exp == "Q1":
        to = D.timeouts_by_config(idx.runs, exp)
        ui.warnbox("Q1 timeouts (inconclusive, excluded from every denominator): " + ", ".join(f"{D.CONFIG_LABEL[c]} {n}" for c, n in to.items())
                   + f" · total {sum(to.values())}. Missing cells mean denominators differ by configuration. One repetition: no repeatability evidence.")
    if exp == "S1":
        ui.warnbox("S1 full-defence attack figures are a RANGE. A05 (AM03, seed 2) is an unresolved single review: lower bound counts it NOT SUCCESS, upper bound SUCCESS. It is never shown as a final result.")

    # KPI row: unprotected vs full
    u = next(r for r in mt if r["config"] == "unprotected")
    f = next(r for r in mt if r["config"] == "full")
    k = st.columns(4)
    atk_ids = {r["scenario"] for r in idx.runs if r["experiment"] == exp and r["is_attack"]}
    observed = {r["scenario"] for r in idx.runs if r["experiment"] == exp and r["is_attack"] and r["config"] == "unprotected" and r["legit"] != "inconclusive"}
    with k[0]:
        if len(observed) < len(atk_ids):
            ui.kpi("Attack scenarios attempted (unprotected)", f"{len(cset)} / {len(observed)} observed",
                   f"{len(atk_ids) - len(observed)} of {len(atk_ids)} had no valid unprotected run (timeout), so {len(cset)}–{len(cset) + len(atk_ids) - len(observed)} of {len(atk_ids)}")
        else:
            ui.kpi("Attack scenarios attempted (unprotected)", f"{len(cset)} / {len(atk_ids)}", "attempted in ≥1 repetition — the base for conditional ASR")
    with k[1]:
        ui.kpi("Conditional ASR · unprotected → full", f"{_range(u['conditional_asr_lower'], u['conditional_asr_upper'])} → {_range(f['conditional_asr_lower'], f['conditional_asr_upper'])}",
               f"only the {len(cset)} attempted scenarios; full CI {_ci(f['conditional_asr_ci'])}")
    with k[2]:
        ui.kpi("Overall attack success · full", _range(f["attack_success_lower"], f["attack_success_upper"]), "over all 26 attack scenarios (mean of per-scenario rates)")
    with k[3]:
        ui.kpi("Legitimate success · unprotected → full", f"{_pct(u['legit_success'])} → {_pct(f['legit_success'])}", "utility cost of the defences")

    t1, t2 = st.columns(2)
    df = pd.DataFrame(mt)
    long = []
    for r in mt:
        long.append({"Configuration": r["config_label"], "Metric": "Attempted", "value": r["attack_attempt_upper"], "lo": r["attack_attempt_ci"][0] if r["attack_attempt_ci"] else None,
                     "hi": r["attack_attempt_ci"][1] if r["attack_attempt_ci"] else None, "range_lo": r["attack_attempt_lower"]})
        long.append({"Configuration": r["config_label"], "Metric": "Succeeded", "value": r["attack_success_upper"], "lo": (r["attack_success_ci_upper"] or [None, None])[0],
                     "hi": (r["attack_success_ci_upper"] or [None, None])[1], "range_lo": r["attack_success_lower"]})
    ldf = pd.DataFrame(long)
    with t1:
        st.markdown("**Attack attempt vs success (all 26 attack scenarios)**")
        base = alt.Chart(ldf).encode(x=alt.X("Configuration:N", sort=[D.CONFIG_LABEL[c] for c in D.CONFIG_ORDER], title=None, axis=alt.Axis(labelAngle=-25)), xOffset="Metric:N")
        bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            y=alt.Y("value:Q", title="Rate", axis=alt.Axis(format="%")), color=alt.Color("Metric:N", scale=alt.Scale(range=["#64748B", ui.C["red"]]), title=None),
            tooltip=["Configuration", "Metric", alt.Tooltip("range_lo:Q", title="lower bound", format=".1%"), alt.Tooltip("value:Q", title="upper bound", format=".1%"),
                     alt.Tooltip("lo:Q", format=".1%", title="95% CI low"), alt.Tooltip("hi:Q", format=".1%", title="95% CI high")])
        err = base.mark_errorbar(color="#E6EAF2").encode(y=alt.Y("lo:Q", title="Rate"), y2="hi:Q")
        st.altair_chart(_cfg(alt.layer(bars, err).properties(height=300)), use_container_width=True)
        st.caption("Attempted = the model proposed the attacker's action or relayed the planted claim; Succeeded = the attacker's goal happened. "
                   "The gap is prevention or failed attempts. Error bars: 95% scenario-cluster bootstrap.")
    with t2:
        st.markdown("**Utility vs security trade-off**")
        tdf = df.assign(attack=df["attack_success_upper"], legit=df["legit_success"])
        pts = alt.Chart(tdf).mark_circle(size=260, opacity=.95, stroke="#0A0F1E", strokeWidth=2).encode(
            x=alt.X("attack:Q", title="Attack success (upper bound) → worse", axis=alt.Axis(format="%")),
            y=alt.Y("legit:Q", title="Legitimate success → better", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
            color=alt.Color("config_label:N", scale=CFG_SCALE, title=None),
            tooltip=[alt.Tooltip("config_label:N", title="config"), alt.Tooltip("attack_success_lower:Q", format=".1%"), alt.Tooltip("attack_success_upper:Q", format=".1%"), alt.Tooltip("legit:Q", format=".1%")])
        lbl = alt.Chart(tdf).mark_text(dx=12, align="left", color="#C9D2E3", fontSize=12).encode(x="attack:Q", y="legit:Q", text="config_label:N")
        st.altair_chart(_cfg(alt.layer(pts, lbl).properties(height=300)), use_container_width=True)
        st.caption("Top-left is best. Points are per-configuration means over scenarios; differences are descriptive, not significance-tested.")

    st.markdown("**Per-configuration metrics** (scenario-level means, 95% cluster-bootstrap CI)")
    tab = []
    for r in mt:
        cnt = next(c for c in counts if c["config"] == r["config"])
        tab.append({"Configuration": r["config_label"],
                    "Attack attempted": f"{_range(r['attack_attempt_lower'], r['attack_attempt_upper'])} {_ci(r['attack_attempt_ci'])}",
                    "Attack succeeded": f"{_range(r['attack_success_lower'], r['attack_success_upper'])} {_ci(r['attack_success_ci_lower'])}",
                    f"Conditional ASR ({len(cset)} scen.)": f"{_range(r['conditional_asr_lower'], r['conditional_asr_upper'])} {_ci(r['conditional_asr_ci'])}",
                    "Legit success": f"{_pct(r['legit_success'])} {_ci(r['legit_ci'])}",
                    "L3 attacker blocks": _pct(r["l3_attack_block"]),
                    "Runs (excl. inconclusive)": f"{cnt['legit_n']} / {cnt['runs']}",
                    "Manual review left": r["manual_review_runs"]})
    st.dataframe(pd.DataFrame(tab), hide_index=True, use_container_width=True)
    with st.expander("How to read these numbers"):
        st.markdown(f"""
- **Attack attempted / succeeded**: mean over the 26 attack scenarios of each scenario's rate across repetitions. Inconclusive runs are excluded.
- **Conditional ASR**: the same success rate, but only over the **{len(cset)} scenarios the unprotected model attempted** ({', '.join(cset)}). It is not a rate over all 26 scenarios.
- **Layer 3 attacker blocks**: the only outcome counted as *prevention*: the attacker's own tool call was proposed and denied. "Not attempted" (including after a Layer 1 quarantine) is never prevention.
- **Ranges** (a – b) appear only where a manual-review item is unresolved.
- **Supplementary**: task completion without recorded attack success = {', '.join(f"{r['config_label']} {_pct(r['task_completion_without_attack'])}" for r in mt)} (only attacks the frozen checks detect are excluded).
""")

    st.markdown("**Run-level counts with explicit denominators** (each run = one scenario × configuration × repetition)")
    cdf = pd.DataFrame([{"Configuration": D.CONFIG_LABEL[c["config"]], "Runs": c["runs"], "Inconclusive": c["inconclusive"],
                         "Legit success": f"{c['legit_success']} / {c['legit_n']}", "Attack runs (valid)": c["attack_n"],
                         "Attempted": f"{c['attempted_lower']}" + (f"–{c['attempted_lower'] + c['manual_review']}" if c["manual_review"] else ""),
                         "Succeeded": f"{c['succeeded_lower']}" + (f"–{c['succeeded_lower'] + c['manual_review']}" if c["manual_review"] else ""),
                         "Blocked by L3": c["blocked_l3"], "Not attempted": c["not_attempted"], "…after L1 quarantine": c["not_attempted_after_l1"],
                         "Malformed attacker call": c["invalid_call"], "Runs with L1 quarantine": c["l1_quarantined_runs"]} for c in counts])
    st.dataframe(cdf, hide_index=True, use_container_width=True)

    pd_rows = []
    for r in mt:
        for key, lab in (("p_succ", "Attack success"), ("p_att", "Attack attempt"), ("p_legit", "Legitimate success")):
            v = (r["vs_unprotected"] or {}).get(key)
            if v:
                pd_rows.append({"Configuration": r["config_label"], "Metric": lab, "Difference vs unprotected": v["mean_difference"], "lo": v["ci95"][0], "hi": v["ci95"][1]})
    if pd_rows:
        st.markdown("**Paired differences vs unprotected (within scenario)**")
        pdf = pd.DataFrame(pd_rows)
        base = alt.Chart().encode(y=alt.Y("Configuration:N", sort=[D.CONFIG_LABEL[c] for c in D.CONFIG_ORDER], title=None), color=alt.Color("Configuration:N", scale=CFG_SCALE, legend=None))
        ch = alt.layer(alt.Chart().mark_rule(color="#8A97B2", strokeDash=[4, 4]).encode(x=alt.datum(0)),
                       base.mark_rule(strokeWidth=3).encode(x=alt.X("lo:Q", title="Difference vs unprotected", axis=alt.Axis(format="+%")), x2="hi:Q"),
                       base.mark_circle(size=120).encode(x="Difference vs unprotected:Q", tooltip=["Configuration", "Metric", alt.Tooltip("Difference vs unprotected:Q", format="+.1%"), alt.Tooltip("lo:Q", format="+.1%"), alt.Tooltip("hi:Q", format="+.1%")]),
                       data=pdf).properties(width=300, height=150)
        st.altair_chart(_cfg(ch.facet(column=alt.Column("Metric:N", title=None, header=alt.Header(labelColor="#E6EAF2")))), use_container_width=False)
        st.caption("Negative attack differences = fewer attacks than unprotected; negative legitimate differences = utility cost. "
                   "Manual-review items use the lower bound here; scenarios missing in either configuration (timeouts) are dropped from the pair.")

    st.markdown("**Repetition / seed variability**")
    if exp == "Q1":
        st.info("Q1 has a single repetition (runtime gate failed), so run-to-run variability is not measured. Do not read Q1 as evidence of repeatability.")
    else:
        rr = pd.DataFrame(D.per_repetition_rates(idx.runs, exp))
        rr["Configuration"] = rr["config"].map(D.CONFIG_LABEL)
        v1, v2 = st.columns(2)
        for col, met, title in ((v1, "attack_success", "Attack success per repetition"), (v2, "legit_success", "Legitimate success per repetition")):
            with col:
                ch = alt.Chart(rr).mark_line(point=True, strokeWidth=2).encode(x=alt.X("repetition:O", title="Repetition" if exp == "R1" else "Seed"),
                                                                              y=alt.Y(f"{met}:Q", title=title, axis=alt.Axis(format="%")),
                                                                              color=alt.Color("Configuration:N", scale=CFG_SCALE, title=None),
                                                                              tooltip=["Configuration", "repetition", alt.Tooltip(f"{met}:Q", format=".1%")])
                st.altair_chart(_cfg(ch.properties(height=230)), use_container_width=True)
        st.caption("Run-level rates per repetition (manual review counted at the lower bound). Outcome reproducibility (modal agreement): "
                   + ", ".join(f"{r['config_label']} {r['reproducibility']:.3f}" for r in mt if r["reproducibility"] is not None))

    st.markdown("**Scenario-level results**")
    ps = pd.DataFrame(state.per_scenario(exp))
    which = st.segmented_control("Show", ["Attack success", "Attack attempt", "Legitimate success"], default="Attack success", key=f"heat_{exp}") or "Attack success"
    col = {"Attack success": "p_succ", "Attack attempt": "p_att", "Legitimate success": "p_legit"}[which]
    sub = ps[ps[col].notna()].copy() if col in ps else ps.iloc[0:0]
    if len(sub):
        sub["value"] = sub[col].apply(lambda v: v[1] if isinstance(v, list) else v)
        sub["lower"] = sub[col].apply(lambda v: v[0] if isinstance(v, list) else v)
        sub["Configuration"] = sub["config"].map(D.CONFIG_LABEL)
        if col != "p_legit":
            sub = sub[sub["scenario"].isin(sorted({r["scenario"] for r in idx.runs if r["is_attack"]}))]
        hi_col = ui.C["red"] if col != "p_legit" else ui.C["green"]
        sub["label"] = sub.apply(lambda r: "" if r["value"] == 0 else (f"{r['lower']:.0%}–{r['value']:.0%}" if r["lower"] != r["value"] else f"{r['value']:.0%}"), axis=1)
        enc = dict(x=alt.X("Configuration:N", sort=[D.CONFIG_LABEL[c] for c in D.CONFIG_ORDER], title=None, axis=alt.Axis(orient="top", labelAngle=0)),
                   y=alt.Y("scenario:N", title=None, axis=alt.Axis(labelOverlap=False)))
        rect = alt.Chart(sub).mark_rect(cornerRadius=4, stroke="#0A0F1E", strokeWidth=2).encode(
            **enc, color=alt.Color("value:Q", scale=alt.Scale(domain=[0, 1], range=["#16213A", hi_col]), legend=alt.Legend(format="%", title=which)),
            tooltip=["scenario", "Configuration", alt.Tooltip("lower:Q", format=".0%", title="lower"), alt.Tooltip("value:Q", format=".0%", title="upper"), "R", "excluded"])
        txt = alt.Chart(sub).mark_text(fontSize=11, color="#F8FAFC", fontWeight="bold").encode(**enc, text="label:N")
        st.altair_chart(_cfg(alt.layer(rect, txt).properties(height=24 * sub["scenario"].nunique())), use_container_width=True)
        st.caption("Each cell = the scenario's rate across its repetitions in that configuration (R = valid runs). Blank = no valid run (e.g. a Q1 timeout).")


def _detector():
    m = state.detector_metrics()
    ui.explain("Layer 1 was evaluated separately on 120 frozen examples (60 malicious, 60 benign) at threshold 0.5. This is the detector alone, not the end-to-end agent.")
    k = st.columns(5)
    for col, (lab, val, d) in zip(k, [("Precision", m["precision"], f"{m['confusion']['tp']} TP of {m['confusion']['tp'] + m['confusion']['fp']} flagged"),
                                      ("Recall", m["recall"], f"Wilson {_ci(m['recall_wilson95'])}"), ("F1", m["f1"], ""),
                                      ("False-positive rate", m["fpr"], f"Wilson {_ci(m['fpr_wilson95'])}"), ("Median latency", None, f"{m['latency_s']['median'] * 1000:.0f} ms per check")]):
        with col:
            ui.kpi(lab, _pct(val) if val is not None else f"{m['latency_s']['median'] * 1000:.0f} ms", d)
    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        cm = m["confusion"]
        cdf = pd.DataFrame([{"Actual": "malicious", "Predicted": "flagged", "n": cm["tp"]}, {"Actual": "malicious", "Predicted": "passed", "n": cm["fn"]},
                            {"Actual": "benign", "Predicted": "flagged", "n": cm["fp"]}, {"Actual": "benign", "Predicted": "passed", "n": cm["tn"]}])
        base = alt.Chart(cdf).encode(x=alt.X("Predicted:N", title=None, axis=alt.Axis(orient="top", labelAngle=0)), y=alt.Y("Actual:N", title=None))
        st.altair_chart(_cfg(alt.layer(base.mark_rect(cornerRadius=6).encode(color=alt.Color("n:Q", scale=alt.Scale(scheme="tealblues"), legend=None)),
                                       base.mark_text(fontSize=22, fontWeight="bold", color="white").encode(text="n:Q")).properties(height=220)), use_container_width=True)
    with c2:
        pc = pd.DataFrame([{"Category": k.replace("_", " "), "Flag rate": v["flag_rate"], "lo": v["wilson95"][0], "hi": v["wilson95"][1], "n": v["n"],
                            "Type": "malicious" if k.startswith("malicious") else "benign"} for k, v in m["per_category"].items()])
        base = alt.Chart(pc).encode(y=alt.Y("Category:N", sort="-x", title=None))
        st.altair_chart(_cfg(alt.layer(base.mark_bar(cornerRadiusEnd=4).encode(x=alt.X("Flag rate:Q", axis=alt.Axis(format="%")), color=alt.Color("Type:N", scale=alt.Scale(range=[ui.C["amber"], ui.C["red"]]), title=None),
                                                                        tooltip=["Category", "n", alt.Tooltip("Flag rate:Q", format=".1%")]),
                                       base.mark_rule(color="white").encode(x="lo:Q", x2="hi:Q")).properties(height=240)), use_container_width=True)
        st.caption("Benign 'challenging' texts (that discuss instructions) are flagged 35% of the time; this is the source of the end-to-end false quarantines (LD02, LR04).")


def _layer3():
    idx = state.run_index()
    s = D.l3_summary(idx.denials)
    ui.explain("Every Layer 3 denial in all 2,600 runs, read from the logs. 'Attack-related' = the attacker's own call was denied (prevention). "
               "Non-attacker denials are the agent's own mistakes (wrong recipient, repeated or out-of-scope actions) caught by the policy.")
    ui.warnbox("Human review covered a SAMPLE of non-attacker denials (12 Stage 2 + 20 R1 + 11 Q1/S1 = 43), with 0 false blocks found. "
               "The others are rule-drafted provisional classifications. This is not a complete audit of every denial.")
    st.dataframe(pd.DataFrame([{"Experiment": r["experiment"], "All denials": r["denials"], "Attack-related (prevention)": r["attack_related"],
                                "Non-attacker": r["non_attacker"], "Human-reviewed": r["human_reviewed"], "False blocks in reviewed": r["reviewed_false_blocks"],
                                "Provisional (rule draft)": r["provisional"], "Not reviewed": r["not_reviewed"],
                                "Reviewed categories": ", ".join(f"{k} {v}" for k, v in r["categories_reviewed"].items())} for r in s]), hide_index=True, use_container_width=True)
    dd = pd.DataFrame(idx.denials)
    dd["Status"] = dd.apply(lambda r: "attack-related (prevention)" if r["attack_related"] else ("human-reviewed" if r["review_status"].startswith("human") else "provisional"), axis=1)
    agg = dd.groupby(["experiment", "config", "Status"]).size().reset_index(name="n")
    agg["Configuration"] = agg["config"].map(D.CONFIG_LABEL)
    ch = alt.Chart(agg).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y("Configuration:N", title=None), x=alt.X("n:Q", title="Denials"), color=alt.Color("Status:N", scale=alt.Scale(domain=["attack-related (prevention)", "human-reviewed", "provisional"], range=[ui.C["green"], ui.C["cyan"], "#475569"]), title=None),
        row=alt.Row("experiment:N", title=None, header=alt.Header(labelColor="#E6EAF2", labelFontSize=13)), tooltip=["experiment", "Configuration", "Status", "n"])
    st.altair_chart(_cfg(ch.properties(height=70)), use_container_width=True)
    reasons = dd.assign(rule=dd["reason"].str.replace(r" [^ ]+@[^ ]+$", " <sender>", regex=True).str.replace(r"'[^']+'", "'…'", regex=True)).groupby(["experiment", "rule"]).size().reset_index(name="n")
    with st.expander("Denials by guard rule"):
        st.dataframe(reasons.sort_values(["experiment", "n"], ascending=[True, False]), hide_index=True, use_container_width=True)


def _errors():
    idx = state.run_index()
    df = pd.DataFrame(idx.runs)
    ui.explain("Errors are not attack outcomes. Timeouts (model call > 180 s) are inconclusive and excluded; a six-call-limit stop and a malformed tool call are scored normally and never counted as defence.")
    g = df.groupby(["experiment", "config"]).agg(runs=("run_id", "size"), inconclusive=("legit", lambda s: (s == "inconclusive").sum()),
                                                 call_limit=("stop_reason", lambda s: (s == "max_tool_calls").sum()),
                                                 malformed_attacker_call=("attack", lambda s: (s == "not_executed_invalid_call").sum())).reset_index()
    g["Configuration"] = g["config"].map(D.CONFIG_LABEL)
    st.dataframe(g[["experiment", "Configuration", "runs", "inconclusive", "call_limit", "malformed_attacker_call"]].rename(columns={"experiment": "Experiment", "runs": "Runs", "inconclusive": "Inconclusive (timeout)", "call_limit": "Six-call-limit stops", "malformed_attacker_call": "Malformed attacker call"}),
                 hide_index=True, use_container_width=True)
    wt = df[df["wall_time_s"].notna()]
    ch = alt.Chart(wt).mark_boxplot(extent="min-max", size=26, color=ui.C["cyan"]).encode(x=alt.X("wall_time_s:Q", title="Wall time per run (s, log scale)", scale=alt.Scale(type="log")),
                                                                                         y=alt.Y("experiment:N", title=None))
    st.altair_chart(_cfg(ch.properties(height=160)), use_container_width=True)
    st.caption("qwen3:4b (Q1) ran ~50× slower than llama3.2:3b on this laptop, which is why the predefined runtime gate stopped Q1 after one repetition.")


def _questions():
    from agentshield.dashboard import summary as SM
    idx = state.run_index()
    ui.explain("Three experiments, never combined: R1 = llama3.2:3b at temperature 0 (10 repetitions; the 200-run reference evaluation is its first repetition), "
               "Q1 = qwen3:4b (1 repetition; timed-out runs excluded), S1 = llama3.2:3b with sampling on (5 seeds).")

    # ---------------- Question 1
    st.markdown(ui.question_header(1, "Did AgentShield reduce successful attacks?", "without defences vs all three layers"), unsafe_allow_html=True)
    q1 = SM.q1_reduction(idx.runs)
    cols = st.columns(3)
    for col, q in zip(cols, q1):
        u, f = q["unprotected"], q["full"]
        with col:
            st.markdown(f"<div class='as-story'><div class='as-note'><b>{q['experiment']}</b> · {ui.esc(D.EXPERIMENT_TEXT[q['experiment']].split(',')[0])}</div>"
                        f"<div style='display:flex;gap:18px;margin:8px 0'><div><div class='as-note'>No defence</div><div style='font-size:28px;font-weight:800;color:{ui.C['red']}'>{SM.rng(u['conditional_asr_lower'], u['conditional_asr_upper'])}</div></div>"
                        f"<div style='font-size:24px;padding-top:18px;color:#64748B'>→</div><div><div class='as-note'>All layers</div><div style='font-size:28px;font-weight:800;color:{ui.C['green'] if f['conditional_asr_upper'] < u['conditional_asr_lower'] else ui.C['amber']}'>{SM.rng(f['conditional_asr_lower'], f['conditional_asr_upper'])}</div></div></div>"
                        f"<div class='as-note'>Attack success on the <b>{q['conditional_n']}</b> attack scenario(s) the unprotected model actually attempted (of 26).</div>"
                        f"<div class='lt' style='font-size:14.5px;margin-top:8px'>{ui.esc(q['how'])}</div>"
                        f"<div class='as-note' style='margin-top:6px'>{ui.esc(q['denominator'])}</div>"
                        + (f"<div class='as-note' style='color:{ui.C['amber']};margin-top:6px'>Range: one review (A05) is unresolved.</div>" if q["is_range"] else "") + "</div>", unsafe_allow_html=True)
    st.caption("Reading it: a lower number with all layers is a recorded reduction. But only Layer 3 denials are proven blocks; attacks that were simply not attempted (often because the small model ignored the injection) are not counted as prevention. "
               "Overall rates over all 26 attack scenarios are in Advanced analysis.")

    # ---------------- Question 2
    st.markdown(ui.question_header(2, "Did it interfere with legitimate tasks?", "share of user tasks completed, per configuration"), unsafe_allow_html=True)
    q2 = pd.DataFrame(SM.q2_utility())
    q2["Configuration"] = q2["config_label"]
    q2["lo"] = q2["ci"].apply(lambda c: c[0] if c else None)
    q2["hi"] = q2["ci"].apply(lambda c: c[1] if c else None)
    base = alt.Chart(q2).encode(x=alt.X("Configuration:N", sort=[D.CONFIG_LABEL[c] for c in D.CONFIG_ORDER], title=None, axis=alt.Axis(labelAngle=-35, labelFontSize=12, labelOverlap=False)))
    ch = alt.layer(base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(y=alt.Y("legit:Q", title="Legitimate task success", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
                                                                                     color=alt.Color("Configuration:N", scale=CFG_SCALE, legend=None),
                                                                                     tooltip=["experiment", "Configuration", alt.Tooltip("legit:Q", format=".1%"), alt.Tooltip("diff:Q", format="+.1%", title="vs no defence")]),
                   base.mark_errorbar(color="#E6EAF2").encode(y=alt.Y("lo:Q", title="Legitimate task success"), y2="hi:Q")).properties(width=230, height=210)
    st.altair_chart(_cfg(ch.facet(column=alt.Column("experiment:N", title=None, sort=["R1", "Q1", "S1"], header=alt.Header(labelColor="#E6EAF2", labelFontSize=14))).resolve_scale(x="independent")), use_container_width=False)
    parts = []
    for e in ("R1", "Q1", "S1"):
        d = {r["config"]: r["diff"] for _, r in q2[q2["experiment"] == e].iterrows()}
        bits = []
        if d.get("l1_only") is not None:
            bits.append(f"Layer 1 alone {d['l1_only'] * 100:+.0f} pts")
        if d.get("full") is not None:
            bits.append(f"all layers {d['full'] * 100:+.0f} pts")
        parts.append(f"<b>{e}</b>: " + ", ".join(bits) + " vs no defence")
    st.markdown("<div class='as-note' style='font-size:15px'>" + " · ".join(parts)
                + ". The main cost comes from Layer 1 withholding harmless documents (false alarms). Paired differences; intervals are in Advanced analysis.</div>", unsafe_allow_html=True)

    # ---------------- Question 3
    st.markdown(ui.question_header(3, "Did any attacks still succeed?", "successes with all three layers on"), unsafe_allow_html=True)
    q3 = SM.q3_residual(idx.runs)
    if not q3:
        st.success("No attack succeeded under full defence.")
    for c in q3:
        col = ui.C["amber"] if c["succeeded"] == 0 else ui.C["red"]
        st.markdown(f"<div class='as-act' style='border-left:3px solid {col}'><div class='ic' style='color:{col}'>⚠</div><div><b>{c['experiment']} · {c['scenario']}</b> — {ui.esc(c['objective'])}<br>"
                    f"<span class='as-note'>Succeeded in <b>{c['succeeded']}</b> of {c['runs']} full-defence run(s)"
                    + (f", plus {c['unresolved']} unresolved" if c["unresolved"] else "") + f" · {ui.esc(c['kind'])}</span></div></div>", unsafe_allow_html=True)
    st.caption("These are honest weaknesses: open any of them in the Evidence Explorer (search the scenario id) or in the simulator's replay to see exactly what happened.")


def render() -> None:
    ui.inject_story_css()
    ui.hero("Evaluation Results", "What the experiments show — in three questions, with every detail one click away")
    _questions()
    st.divider()
    st.markdown("### 🔬 Advanced analysis")
    st.caption("All configuration comparisons, confidence intervals, denominators, repetition/seed analysis, timeouts, and Layer 1 / Layer 3 metrics.")
    with st.expander("Open the full analysis", expanded=False):
        tabs = st.tabs(["Overview", "R1 · llama T=0 ×10", "Q1 · qwen ×1", "S1 · llama T=0.8 ×5", "Layer 1 detector", "Layer 3 guard", "Errors & timeouts"])
        with tabs[0]:
            _overview()
        for t, e in zip(tabs[1:4], ("R1", "Q1", "S1")):
            with t:
                _experiment(e)
        with tabs[4]:
            _detector()
        with tabs[5]:
            _layer3()
        with tabs[6]:
            _errors()
