"""Cached access to the read-only back end (agentshield.dashboard.*)."""

from __future__ import annotations

import streamlit as st

from agentshield.dashboard import data as D
from agentshield.frozen import load_frozen_suite, verify_frozen


@st.cache_resource(show_spinner="Indexing 2,600 run logs…")
def _index():
    return D.build_run_index()


def run_index():
    return _index()


@st.cache_resource(show_spinner=False)
def suite():
    return load_frozen_suite(verify_frozen())


@st.cache_data(show_spinner=False)
def overview():
    return D.overview(_index().runs)


@st.cache_data(show_spinner=False)
def metric_table(exp: str):
    return D.metric_table(exp)


@st.cache_data(show_spinner=False)
def per_scenario(exp: str):
    return D.per_scenario(exp)


@st.cache_data(show_spinner=False)
def conditional_set(exp: str):
    return D.conditional_set(exp)


@st.cache_data(show_spinner=False)
def detector_metrics():
    return D.detector_metrics()


@st.cache_data(show_spinner=False, ttl=15)
def runtime_status(model: str):
    from agentshield.dashboard.live import check_runtime
    return check_runtime(model)
