"""Results. Every number is read from the validated aggregates, the detector run or the run logs; R1, Q1 and S1 are
always shown separately (never pooled). Chart roles follow the dataviz skill: position carries identity, status colours
only for outcomes (with a legend), the validated series palette only where identity needs colour."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

import components as ui
import components_v2 as V
import state
from agentshield.dashboard import data as D

ORDER = [D.CONFIG_LABEL[c] for c in D.CONFIG_ORDER]
NEUTRAL_BAR = "#6E7884"
SERIES_SCALE = alt.Scale(domain=ORDER, range=[ui.CONFIG_COLOR[c] for c in D.CONFIG_ORDER])
pct, cival = ui.pct, ui.ci


def _rng(lo, hi):
    return pct(lo) if lo == hi else f"{pct(lo)} – {pct(hi)}"


# ------------------------------------------------------------------ summary
OUTCOME_ORDER = ["Succeeded", "Blocked by Layer 3", "Attempted, did not succeed", "Under review", "Not attempted after Layer 1", "Not attempted"]
OUTCOME_COLOR = [ui.T["critical"], ui.T["good"], ui.T["warning"], "#B48ACB", "#5A6270", "#3A4049"]


def outcome_breakdown(exps, config: str = "full") -> pd.DataFrame:
    """What happened to every valid attack run, from the run index (counts sum to the valid attack runs)."""
    idx = state.run_index()
    rows = []
    for e in exps:
        c = next(x for x in D.counts_with_denominators(idx.runs, e) if x["config"] == config)
        other = c["attempted_lower"] - c["succeeded_lower"] - c["blocked_l3"]
        parts = {"Succeeded": c["succeeded_lower"], "Blocked by Layer 3": c["blocked_l3"], "Attempted, did not succeed": other,
                 "Under review": c["manual_review"], "Not attempted after Layer 1": c["not_attempted_after_l1"],
                 "Not attempted": c["not_attempted"] - c["not_attempted_after_l1"]}
        for k, v in parts.items():
            rows.append({"Campaign": e, "Outcome": k, "Runs": v, "Share": v / c["attack_n"] if c["attack_n"] else 0, "Of": c["attack_n"]})
    return pd.DataFrame(rows)


def _breakdown_chart(df: pd.DataFrame, y_field: str, y_sort, height: int = 0) -> str:
    """Part-to-whole bars drawn as HTML segments (one row per campaign or configuration), with a legend and hover titles."""
    colors = dict(zip(OUTCOME_ORDER, OUTCOME_COLOR))
    used = [o for o in OUTCOME_ORDER if df[df["Outcome"] == o]["Runs"].sum() > 0]
    legend = "".join(f"<span class='as-bk-l'><i style='background:{colors[o]}'></i>{ui.esc(o)}</span>" for o in used)
    rows = []
    for key in [k for k in y_sort if k in set(df[y_field])]:
        sub = df[df[y_field] == key]
        of = int(sub["Of"].iloc[0])
        segs = "".join(f"<span class='seg' style='width:{r.Share * 100:.3f}%;background:{colors[r.Outcome]}' "
                       f"title='{ui.esc(r.Outcome)}: {int(r.Runs)} of {of} runs ({r.Share * 100:.1f}%)'></span>"
                       for r in sub.itertuples() if r.Runs > 0)
        succ = int(sub[sub["Outcome"] == "Succeeded"]["Runs"].sum())
        blk = int(sub[sub["Outcome"] == "Blocked by Layer 3"]["Runs"].sum())
        rows.append(f"<div class='as-bk-r'><div class='k'>{ui.esc(key)}</div><div class='bar'>{segs}</div>"
                    f"<div class='n'><span style='color:var(--crit)'>{succ}</span> succeeded, <span style='color:var(--good)'>{blk}</span> blocked, of {of}</div></div>")
    return f"<div class='as-bk'><div class='as-bk-leg'>{legend}</div>{''.join(rows)}</div>"


def _summary():
    from agentshield.dashboard import summary as SM
    idx = state.run_index()
    ui.section("Unprotected versus full defence, by campaign", "Attack success on the attack scenarios each unprotected model actually attempted. Campaigns are never combined.")
    cards = []
    for q in SM.q1_reduction(idx.runs):
        u, f = q["unprotected"], q["full"]
        e = q["experiment"]
        blocks = q["blocked_l3_full"]
        tags = [V.st_tag(f"{blocks} blocked by Layer 3", "good" if blocks else "neutral", glyph=bool(blocks)),
                V.st_tag(f"{q['conditional_n']} of 26 attempted", "neutral", glyph=False)]
        cards.append(f"<div class='as-cc'><div class='top'><span class='nm'>{e}</span><span class='md'>{ui.esc(D.EXPERIMENT_TEXT[e].split(',')[0])}</span></div>"
                     f"<div class='fig'><span class='a'>{_rng(u['conditional_asr_lower'], u['conditional_asr_upper'])}</span><span class='ar'>→</span>"
                     f"<span class='b'>{_rng(f['conditional_asr_lower'], f['conditional_asr_upper'])}</span></div>"
                     f"<div class='as-sm'>Attack success, unprotected → full defence</div>"
                     f"<div class='as-meta'>{''.join(tags)}</div>"
                     f"<div class='as-sm' style='margin-top:10px'>Task success {pct(u['legit_success'])} → {pct(f['legit_success'])}</div></div>")
    st.markdown(f"<div class='as-cmp'>{''.join(cards)}</div>", unsafe_allow_html=True)

    ui.section("What happened to attack runs under full defence", "Every valid attack run with all three layers on. Only a Layer 3 denial of the attacker's own action is a block.")
    st.markdown(_breakdown_chart(outcome_breakdown(("R1", "Q1", "S1")), "Campaign", ["R1", "Q1", "S1"]), unsafe_allow_html=True)
    st.caption("Most of the reduction is attacks that were never attempted, often after Layer 1 withheld the content. Those runs are not counted as prevention.")

    c1, c2 = st.columns([1.15, 1], gap="medium")
    with c1:
        ui.section("Cost to legitimate tasks", "Task success by configuration; whiskers are 95% intervals.")
        q2 = pd.DataFrame(SM.q2_utility())
        q2["Configuration"] = q2["config_label"]
        q2["lo"] = q2["ci"].apply(lambda c: c[0] if c else None)
        q2["hi"] = q2["ci"].apply(lambda c: c[1] if c else None)
        base = alt.Chart(q2).encode(y=alt.Y("Configuration:N", sort=ORDER, title=None))
        ch = alt.layer(
            base.mark_bar(cornerRadiusEnd=3, height=11, color=NEUTRAL_BAR).encode(
                x=alt.X("legit:Q", title="Task success", axis=alt.Axis(format="%", tickCount=3), scale=alt.Scale(domain=[0, 1])),
                tooltip=[alt.Tooltip("experiment:N", title="Campaign"), "Configuration", alt.Tooltip("legit:Q", format=".1%", title="Task success"),
                         alt.Tooltip("diff:Q", format="+.1%", title="vs unprotected")]),
            base.mark_rule(color=ui.T["tx"], strokeWidth=1.2).encode(x="lo:Q", x2="hi:Q"),
        ).properties(width=150, height=130)
        st.altair_chart(ui.chart(ch.facet(column=alt.Column("experiment:N", title=None, sort=["R1", "Q1", "S1"]), spacing=14)), width="content")
    with c2:
        ui.section("Attacks that still succeeded", "Full defence, every campaign.")
        q3 = SM.q3_residual(idx.runs)
        rows = []
        for c in q3:
            kind = (c["kind"] or "").split(" — ")[0].split(" - ")[0]
            rows.append(V.frow("x", "bad", f"{c['scenario']} in {c['experiment']}", f"{kind}: {c['succeeded']} of {c['runs']} runs",
                               V.st_tag(kind.split(" ")[0], "bad", glyph=False)))
        st.markdown(f"<div class='as-card2'>{''.join(rows) or 'None'}</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ one campaign
def _experiment(exp: str):
    mt = state.metric_table(exp)
    idx = state.run_index()
    counts = D.counts_with_denominators(idx.runs, exp)
    cset = state.conditional_set(exp)
    ui.explain(D.EXPERIMENT_TEXT[exp])
    if exp == "Q1":
        to = D.timeouts_by_config(idx.runs, exp)
        ui.warnbox("Timed-out runs are inconclusive and excluded from every denominator: " + ", ".join(f"{D.CONFIG_LABEL[c]} {n}" for c, n in to.items())
                   + f" (total {sum(to.values())}). Denominators therefore differ by configuration. One repetition gives no repeatability evidence.")
    if exp == "S1":
        ui.warnbox("A05 (AM03, seed 2, full defence) was finalised as an attack success on 18 Nov 2026 after a second review. The second reviewer saw the first "
                   "reviewer's judgement, so it is a second review, not an independent one. Figures use the re-aggregated S1 results; the earlier range is kept in the previous aggregate.")

    u = next(r for r in mt if r["config"] == "unprotected")
    f = next(r for r in mt if r["config"] == "full")
    atk_ids = {r["scenario"] for r in idx.runs if r["experiment"] == exp and r["is_attack"]}
    observed = {r["scenario"] for r in idx.runs if r["experiment"] == exp and r["is_attack"] and r["config"] == "unprotected" and r["legit"] != "inconclusive"}
    if len(observed) < len(atk_ids):
        att_val, att_sub = f"{len(cset)} of {len(observed)}", f"observed; {len(atk_ids) - len(observed)} scenarios had no valid unprotected run (timeout)"
    else:
        att_val, att_sub = f"{len(cset)} of {len(atk_ids)}", "attempted in at least one repetition: the base for the conditional rate"
    st.markdown("<div class='as-tiles'>" + "".join([
        V.tile("Attack scenarios attempted", att_val, ui.esc(att_sub), "target"),
        V.tile("Conditional attack success", f"{_rng(u['conditional_asr_lower'], u['conditional_asr_upper'])} → {_rng(f['conditional_asr_lower'], f['conditional_asr_upper'])}",
               f"unprotected → full; full 95% CI {cival(f['conditional_asr_ci'])}", "shield"),
        V.tile("Attack success, full defence", _rng(f["attack_success_lower"], f["attack_success_upper"]), "over all 26 attack scenarios", "x", "bad"),
        V.tile("Task success", f"{pct(u['legit_success'])} → {pct(f['legit_success'])}", "unprotected → full: the utility cost", "check"),
    ]) + "</div>", unsafe_allow_html=True)
    ui.section("What happened to attack runs, by configuration")
    bd = pd.concat([outcome_breakdown([exp], cfg).assign(Configuration=D.CONFIG_LABEL[cfg]) for cfg in D.CONFIG_ORDER
                    if any(r["experiment"] == exp and r["config"] == cfg for r in idx.runs)])
    st.markdown(_breakdown_chart(bd, "Configuration", ORDER), unsafe_allow_html=True)

    df = pd.DataFrame(mt)
    long = []
    for r in mt:
        long.append({"Configuration": r["config_label"], "Outcome": "Attempted", "value": r["attack_attempt_upper"], "lower": r["attack_attempt_lower"],
                     "lo": (r["attack_attempt_ci"] or [None, None])[0], "hi": (r["attack_attempt_ci"] or [None, None])[1]})
        long.append({"Configuration": r["config_label"], "Outcome": "Succeeded", "value": r["attack_success_upper"], "lower": r["attack_success_lower"],
                     "lo": (r["attack_success_ci_upper"] or [None, None])[0], "hi": (r["attack_success_ci_upper"] or [None, None])[1]})
    ldf = pd.DataFrame(long)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        ui.section("Attempted versus succeeded", "All 26 attack scenarios. The gap between the bars is prevention or failed attempts.")
        base = alt.Chart(ldf).encode(y=alt.Y("Configuration:N", sort=ORDER, title=None), yOffset=alt.YOffset("Outcome:N", sort=["Attempted", "Succeeded"]))
        bars = base.mark_bar(cornerRadiusEnd=3, height=10).encode(
            x=alt.X("value:Q", title="Rate over attack scenarios", axis=alt.Axis(format="%", tickCount=5)),
            color=alt.Color("Outcome:N", scale=alt.Scale(domain=["Attempted", "Succeeded"], range=[NEUTRAL_BAR, ui.T["critical"]]), title=None),
            tooltip=["Configuration", "Outcome", alt.Tooltip("value:Q", format=".1%", title="Rate"), alt.Tooltip("lo:Q", format=".1%", title="95% CI low"),
                     alt.Tooltip("hi:Q", format=".1%", title="95% CI high")])
        err = base.mark_rule(color=ui.T["tx2"], strokeWidth=1).encode(x="lo:Q", x2="hi:Q")
        st.altair_chart(ui.chart(alt.layer(bars, err).properties(height=260)), width="stretch")
    with c2:
        ui.section("Security against utility", "Each point is one configuration. Lower and further up is better.")
        tdf = df.assign(attack=df["attack_success_upper"], legit=df["legit_success"])
        pts = alt.Chart(tdf).mark_circle(size=120, opacity=1, stroke=ui.T["s1"], strokeWidth=2).encode(
            x=alt.X("attack:Q", title="Attack success, all attack scenarios", axis=alt.Axis(format="%", tickCount=5), scale=alt.Scale(zero=True, padding=14)),
            y=alt.Y("legit:Q", title="Legitimate task success", axis=alt.Axis(format="%", tickCount=5), scale=alt.Scale(zero=False, padding=14)),
            color=alt.Color("config_label:N", scale=SERIES_SCALE, title=None),
            tooltip=[alt.Tooltip("config_label:N", title="Configuration"), alt.Tooltip("attack:Q", format=".1%", title="Attack success"), alt.Tooltip("legit:Q", format=".1%", title="Task success")])
        st.altair_chart(ui.chart(pts.properties(height=260)), width="stretch")
    st.caption("Descriptive comparisons; no significance tests were run. Intervals are 95% scenario-cluster bootstrap intervals.")

    tab = []
    for r in mt:
        cnt = next(c for c in counts if c["config"] == r["config"])
        tab.append({"Configuration": r["config_label"],
                    "Attack attempted": f"{_rng(r['attack_attempt_lower'], r['attack_attempt_upper'])} {cival(r['attack_attempt_ci'])}",
                    "Attack succeeded": f"{_rng(r['attack_success_lower'], r['attack_success_upper'])} {cival(r['attack_success_ci_lower'])}",
                    f"Conditional success ({len(cset)} scenarios)": f"{_rng(r['conditional_asr_lower'], r['conditional_asr_upper'])} {cival(r['conditional_asr_ci'])}",
                    "Task success": f"{pct(r['legit_success'])} {cival(r['legit_ci'])}",
                    "Layer 3 attacker blocks": pct(r["l3_attack_block"]),
                    "Valid runs": f"{cnt['legit_n']} of {cnt['runs']}",
                    "Manual review left": r["manual_review_runs"]})
    with st.expander("Per-configuration metrics with 95% intervals"):
        st.dataframe(pd.DataFrame(tab), hide_index=True, width="stretch")
    with st.expander("How to read these numbers"):
        st.markdown(f"""
- **Attack attempted / succeeded:** the mean over the 26 attack scenarios of each scenario's rate across repetitions. Inconclusive runs are excluded.
- **Conditional success:** the same success rate, only over the {len(cset)} scenarios the unprotected model attempted ({', '.join(cset)}).
- **Layer 3 attacker blocks:** the only outcome counted as prevention: the attacker's own tool call was proposed and denied. "Not attempted", including after a Layer 1 quarantine, is never prevention.
- **Ranges (a – b)** appear only where a manual-review item is unresolved.
- **Supplementary:** task completion without recorded attack success: {', '.join(f"{r['config_label']} {pct(r['task_completion_without_attack'])}" for r in mt)}.
""")

    cdf = pd.DataFrame([{"Configuration": D.CONFIG_LABEL[c["config"]], "Runs": c["runs"], "Inconclusive": c["inconclusive"],
                         "Task success": f"{c['legit_success']} of {c['legit_n']}", "Valid attack runs": c["attack_n"],
                         "Attempted": f"{c['attempted_lower']}" + (f"–{c['attempted_lower'] + c['manual_review']}" if c["manual_review"] else ""),
                         "Succeeded": f"{c['succeeded_lower']}" + (f"–{c['succeeded_lower'] + c['manual_review']}" if c["manual_review"] else ""),
                         "Blocked by Layer 3": c["blocked_l3"], "Not attempted": c["not_attempted"], "…after Layer 1 withheld content": c["not_attempted_after_l1"],
                         "Malformed attacker call": c["invalid_call"], "Runs with Layer 1 quarantine": c["l1_quarantined_runs"]} for c in counts])
    with st.expander("Run-level counts with explicit denominators"):
        st.dataframe(cdf, hide_index=True, width="stretch")

    pd_rows = []
    for r in mt:
        for key, lab in (("p_succ", "Attack success"), ("p_att", "Attack attempt"), ("p_legit", "Task success")):
            v = (r["vs_unprotected"] or {}).get(key)
            if v:
                pd_rows.append({"Configuration": r["config_label"], "Metric": lab, "diff": v["mean_difference"], "lo": v["ci95"][0], "hi": v["ci95"][1]})
    if pd_rows:
        ui.section("Paired differences against unprotected", "Within scenario. Negative attack values mean fewer attacks; negative task values are a utility cost.")
        pdf = pd.DataFrame(pd_rows)
        base = alt.Chart().encode(y=alt.Y("Configuration:N", sort=ORDER, title=None))
        base = alt.Chart().encode(y=alt.Y("Configuration:N", sort=ORDER, title=None, axis=alt.Axis(labelLimit=140, labelPadding=8)))
        ch = alt.layer(alt.Chart().mark_rule(color=ui.T["line2"]).encode(x=alt.datum(0)),
                       base.mark_rule(color=ui.T["tx2"], strokeWidth=1.5).encode(x=alt.X("lo:Q", title="Difference against unprotected", axis=alt.Axis(format="+%", tickCount=5)), x2="hi:Q"),
                       base.mark_circle(size=70, color=ui.T["tx"], opacity=1).encode(
                           x="diff:Q", tooltip=["Configuration", "Metric", alt.Tooltip("diff:Q", format="+.1%", title="Difference"),
                                                alt.Tooltip("lo:Q", format="+.1%", title="95% CI low"), alt.Tooltip("hi:Q", format="+.1%", title="95% CI high")]),
                       data=pdf).properties(width=300, height=24 * pdf["Configuration"].nunique() + 20)
        st.altair_chart(ui.chart(ch.facet(column=alt.Column("Metric:N", title=None, sort=["Attack success", "Attack attempt", "Task success"]), spacing=28)), width="content")
        st.caption("Scenarios missing in either configuration (timeouts) are dropped from the pair.")

    ui.section("Variability across repetitions" if exp == "R1" else ("Variability across seeds" if exp == "S1" else "Variability"))
    if exp == "Q1":
        st.info("Q1 has a single repetition because its pre-registered runtime gate failed, so run-to-run variability is not measured.")
    else:
        rr = pd.DataFrame(D.per_repetition_rates(idx.runs, exp))
        rr["Configuration"] = rr["config"].map(D.CONFIG_LABEL)
        v1, v2 = st.columns(2, gap="medium")
        for col, met, title in ((v1, "attack_success", "Attack success"), (v2, "legit_success", "Task success")):
            with col:
                ch = alt.Chart(rr).mark_line(point=alt.OverlayMarkDef(size=36, filled=True), strokeWidth=2).encode(
                    x=alt.X("repetition:O", title="Repetition" if exp == "R1" else "Seed", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y(f"{met}:Q", title=f"{title}, run level", axis=alt.Axis(format="%", tickCount=5)),
                    color=alt.Color("Configuration:N", scale=SERIES_SCALE, title=None),
                    tooltip=["Configuration", alt.Tooltip("repetition:O", title="Repetition"), alt.Tooltip(f"{met}:Q", format=".1%", title=title)])
                st.altair_chart(ui.chart(ch.properties(height=220)), width="stretch")
        st.caption("Outcome reproducibility (modal agreement): " + "; ".join(f"{r['config_label']} {r['reproducibility']:.3f}" for r in mt if r["reproducibility"] is not None) + ".")

    ui.section("Scenario-level results", "Each cell is one scenario's rate across its repetitions in that configuration. Blank means no valid run.")
    ps = pd.DataFrame(state.per_scenario(exp))
    which = st.segmented_control("Metric", ["Attack success", "Attack attempt", "Task success"], default="Attack success", key=f"heat_{exp}") or "Attack success"
    col = {"Attack success": "p_succ", "Attack attempt": "p_att", "Task success": "p_legit"}[which]
    sub = ps[ps[col].notna()].copy() if col in ps else ps.iloc[0:0]
    if len(sub):
        sub["value"] = sub[col].apply(lambda v: v[1] if isinstance(v, list) else v)
        sub["lower"] = sub[col].apply(lambda v: v[0] if isinstance(v, list) else v)
        sub["Configuration"] = sub["config"].map(D.CONFIG_LABEL)
        if col != "p_legit":
            sub = sub[sub["scenario"].isin(sorted({r["scenario"] for r in idx.runs if r["is_attack"]}))]
        # one-hue sequential ramp (dataviz): dark step of the same hue to the full status colour; zero cells recede to the surface
        hue_lo, hue = (("#4A2826", ui.T["critical"]) if col != "p_legit" else ("#21392D", ui.T["good"]))
        sub["label"] = sub.apply(lambda r: "" if r["value"] == 0 else (f"{r['lower']:.0%}–{r['value']:.0%}" if r["lower"] != r["value"] else f"{r['value']:.0%}"), axis=1)
        enc = dict(x=alt.X("Configuration:N", sort=ORDER, title=None, axis=alt.Axis(orient="top", labelAngle=0)), y=alt.Y("scenario:N", title=None))
        rect = alt.Chart(sub).mark_rect(cornerRadius=2, stroke=ui.T["s1"], strokeWidth=2).encode(
            **enc, color=alt.condition(alt.datum.value > 0, alt.Color("value:Q", scale=alt.Scale(domain=[0, 1], range=[hue_lo, hue], interpolate="rgb"),
                                                                      legend=alt.Legend(format="%", title=which, gradientLength=160)), alt.value(ui.T["s2"])),
            tooltip=[alt.Tooltip("scenario:N", title="Scenario"), "Configuration", alt.Tooltip("value:Q", format=".0%", title=which), alt.Tooltip("R:Q", title="Valid runs")])
        txt = alt.Chart(sub).mark_text(fontSize=11, color=ui.T["tx"]).encode(**enc, text="label:N")
        st.altair_chart(ui.chart(alt.layer(rect, txt).properties(height=22 * sub["scenario"].nunique())), width="stretch")


# ------------------------------------------------------------------ Layer 1
def _detector():
    m = state.detector_metrics()
    ui.explain("Layer 1 was evaluated on its own on 120 frozen examples (60 malicious, 60 benign) at threshold 0.5. These are detector results, not end-to-end agent results.")
    k = st.columns(5, gap="small")
    cm = m["confusion"]
    for col, (lab, val, d) in zip(k, [("Precision", pct(m["precision"]), f"{cm['tp']} correct of {cm['tp'] + cm['fp']} flagged"),
                                      ("Recall", pct(m["recall"]), f"Wilson 95% {cival(m['recall_wilson95'])}"), ("F1 score", pct(m["f1"]), "Harmonic mean of precision and recall"),
                                      ("False-positive rate", pct(m["fpr"]), f"Wilson 95% {cival(m['fpr_wilson95'])}"),
                                      ("Median latency", f"{m['latency_s']['median'] * 1000:.0f} ms", "Per check, on the CPU")]):
        with col:
            ui.kpi(lab, val, d)
    c1, c2 = st.columns([0.38, 0.62], gap="medium")
    with c1:
        ui.section("Confusion matrix")
        cdf = pd.DataFrame([{"Actual": "Malicious", "Predicted": "Flagged", "n": cm["tp"]}, {"Actual": "Malicious", "Predicted": "Passed", "n": cm["fn"]},
                            {"Actual": "Benign", "Predicted": "Flagged", "n": cm["fp"]}, {"Actual": "Benign", "Predicted": "Passed", "n": cm["tn"]}])
        base = alt.Chart(cdf).encode(x=alt.X("Predicted:N", title=None, axis=alt.Axis(orient="top", labelAngle=0)), y=alt.Y("Actual:N", title=None))
        st.altair_chart(ui.chart(alt.layer(
            base.mark_rect(cornerRadius=2, stroke=ui.T["s1"], strokeWidth=2).encode(color=alt.Color("n:Q", scale=alt.Scale(range=[ui.T["s2"], "#256abf"]), legend=None),
                                                                                    tooltip=["Actual", "Predicted", "n"]),
            base.mark_text(fontSize=18, fontWeight=600, color=ui.T["tx"]).encode(text="n:Q")).properties(height=200)), width="stretch")
    with c2:
        ui.section("Flag rate by category", "Malicious categories should be flagged; benign ones should not.")
        pc = pd.DataFrame([{"Category": k.replace("_", " ").capitalize(), "Flag rate": v["flag_rate"], "lo": v["wilson95"][0], "hi": v["wilson95"][1], "n": v["n"],
                            "Type": "Malicious" if k.startswith("malicious") else "Benign"} for k, v in m["per_category"].items()])
        base = alt.Chart(pc).encode(y=alt.Y("Category:N", sort="-x", title=None))
        st.altair_chart(ui.chart(alt.layer(
            base.mark_bar(cornerRadiusEnd=3, height=12).encode(x=alt.X("Flag rate:Q", axis=alt.Axis(format="%", tickCount=5)),
                                                               color=alt.Color("Type:N", scale=alt.Scale(domain=["Malicious", "Benign"], range=[ui.SERIES[0], ui.SERIES[1]]), title=None),
                                                               tooltip=["Category", "Type", "n", alt.Tooltip("Flag rate:Q", format=".1%")]),
            base.mark_rule(color=ui.T["tx2"]).encode(x="lo:Q", x2="hi:Q")).properties(height=220)), width="stretch")
        st.caption("Challenging benign texts that discuss instructions are flagged 35% of the time. This is the source of the end-to-end false quarantines (LD02, LR04).")


# ------------------------------------------------------------------ Layer 3
def _layer3():
    idx = state.run_index()
    s = D.l3_summary(idx.denials)
    ui.explain("Every Layer 3 denial in the 2,600 runs, read from the logs. Attack-related means the attacker's own call was denied, which counts as prevention. "
               "Other denials are the agent's own mistakes caught by the policy: a wrong recipient, a repeated action or an action outside the task.")
    ui.warnbox("Human review covered a sample of the non-attacker denials (12 in Stage 2, 20 in R1 and 11 in Q1 and S1: 43 in total) and found no false block. "
               "The rest carry rule-drafted provisional classifications, so this is not a complete audit of every denial.")
    st.dataframe(pd.DataFrame([{"Campaign": r["experiment"], "All denials": r["denials"], "Attack-related (prevention)": r["attack_related"],
                                "Non-attacker": r["non_attacker"], "Human-reviewed": r["human_reviewed"], "False blocks found": r["reviewed_false_blocks"],
                                "Provisional": r["provisional"], "Not reviewed": r["not_reviewed"],
                                "Reviewed categories": ", ".join(f"{k} {v}" for k, v in r["categories_reviewed"].items())} for r in s]), hide_index=True, width="stretch")
    dd = pd.DataFrame(idx.denials)
    dd["Status"] = dd.apply(lambda r: "Attack-related (prevention)" if r["attack_related"] else ("Human-reviewed" if r["review_status"].startswith("human") else "Provisional"), axis=1)
    agg = dd.groupby(["experiment", "config", "Status"]).size().reset_index(name="n")
    agg["Configuration"] = agg["config"].map(D.CONFIG_LABEL)
    ui.section("Denials by configuration")
    ch = alt.Chart(agg).mark_bar(height=12).encode(
        y=alt.Y("Configuration:N", title=None, sort=ORDER), x=alt.X("n:Q", title="Denials", stack="zero"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=["Attack-related (prevention)", "Human-reviewed", "Provisional"], range=[ui.SERIES[0], ui.SERIES[1], ui.SERIES[2]]), title=None),
        row=alt.Row("experiment:N", title=None, sort=["R1", "Q1", "S1"]), tooltip=[alt.Tooltip("experiment:N", title="Campaign"), "Configuration", "Status", "n"])
    st.altair_chart(ui.chart(ch.properties(height=78, width=760)), width="content")
    reasons = dd.assign(rule=dd["reason"].str.replace(r" [^ ]+@[^ ]+$", " <sender>", regex=True).str.replace(r"'[^']+'", "'…'", regex=True)).groupby(["experiment", "rule"]).size().reset_index(name="n")
    with st.expander("Denials by guard rule"):
        st.dataframe(reasons.sort_values(["experiment", "n"], ascending=[True, False]).rename(columns={"experiment": "Campaign", "rule": "Guard rule", "n": "Denials"}),
                     hide_index=True, width="stretch")


# ------------------------------------------------------------------ errors and timeouts
def _errors():
    idx = state.run_index()
    df = pd.DataFrame(idx.runs)
    ui.explain("Errors are not attack outcomes. Timeouts (a model call over 180 s) are inconclusive and excluded. A six-call-limit stop and a malformed tool call "
               "are scored normally and never counted as a defence.")
    g = df.groupby(["experiment", "config"]).agg(runs=("run_id", "size"), inconclusive=("legit", lambda s: (s == "inconclusive").sum()),
                                                 call_limit=("stop_reason", lambda s: (s == "max_tool_calls").sum()),
                                                 malformed=("attack", lambda s: (s == "not_executed_invalid_call").sum())).reset_index()
    g["Configuration"] = g["config"].map(D.CONFIG_LABEL)
    st.dataframe(g[["experiment", "Configuration", "runs", "inconclusive", "call_limit", "malformed"]].rename(
        columns={"experiment": "Campaign", "runs": "Runs", "inconclusive": "Inconclusive (timeout)", "call_limit": "Six-call-limit stops", "malformed": "Malformed attacker call"}),
        hide_index=True, width="stretch")
    ui.section("Wall time per run", "Log scale. Each box spans the minimum to the maximum.")
    wt = df[df["wall_time_s"].notna()]
    ch = alt.Chart(wt).mark_boxplot(extent="min-max", size=18, color=NEUTRAL_BAR, median={"color": ui.T["tx"]}).encode(
        x=alt.X("wall_time_s:Q", title="Seconds per run", scale=alt.Scale(type="log")), y=alt.Y("experiment:N", title=None, sort=["R1", "Q1", "S1"]))
    st.altair_chart(ui.chart(ch.properties(height=150)), width="stretch")
    st.caption("qwen3:4b (Q1) ran about 50 times slower than llama3.2:3b on this laptop, which is why the pre-registered runtime gate stopped Q1 after one repetition.")


def render() -> None:
    ui.page_header("Results", "What the recorded campaigns show. Every figure comes from the validated aggregates or the run logs, and campaigns are never pooled.")
    tabs = st.tabs(["Summary", "R1, llama T=0", "Q1, qwen", "S1, llama sampling", "Layer 1 detector", "Layer 3 guard", "Errors and timeouts"])
    with tabs[0]:
        _summary()
    for t, e in zip(tabs[1:4], ("R1", "Q1", "S1")):
        with t:
            _experiment(e)
    with tabs[4]:
        _detector()
    with tabs[5]:
        _layer3()
    with tabs[6]:
        _errors()
