"""Generate Fig_01_AgentShield_Architecture.png from the implemented pipeline (black and white).

Every label reflects the code as implemented: agent.py (order), guard.py (L3), detector.py (L1),
isolation.py (L2), config.py (six-call limit). Run:
    .venv\\Scripts\\python scripts\\make_fig01_architecture.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "results" / "figures" / "Fig_01_AgentShield_Architecture.png"

plt.rcParams["font.family"] = "DejaVu Sans"
fig, ax = plt.subplots(figsize=(11, 11))
ax.set_xlim(-16, 101)
ax.set_ylim(4, 121)
ax.axis("off")

L, R = 8, 64  # main column edges
CX = (L + R) / 2


def box(x0, x1, y0, y1, title, body, style="solid", lw=1.4, tsize=10.5, bsize=8.6):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0.3,rounding_size=1.0",
                                linewidth=lw, edgecolor="black", facecolor="white", linestyle=style))
    xc = (x0 + x1) / 2
    ax.text(xc, y1 - 1.6, title, ha="center", va="top", fontsize=tsize, fontweight="bold")
    ax.text(xc, y1 - 5.2, body, ha="center", va="top", fontsize=bsize, linespacing=1.4)


def path(points, ls="solid", lw=1.2):
    """Polyline with an arrow head on the last segment."""
    xs, ys = zip(*points)
    ax.plot(xs[:-1], ys[:-1], color="black", linestyle=ls, linewidth=lw)
    ax.annotate("", xy=points[-1], xytext=points[-2],
                arrowprops=dict(arrowstyle="-|>", color="black", lw=lw, linestyle=ls, mutation_scale=13))
    if len(points) > 2:
        ax.plot([xs[-2], xs[-1]], [ys[-2], ys[-1]], color="black", linestyle=ls, linewidth=lw)


def label(x, y, text, rot=0, ha="left", size=8.3):
    ax.text(x, y, text, fontsize=size, style="italic", ha=ha, va="center", rotation=rot)


# ---- main column
Y = {  # (bottom, top)
    "user": (108, 118), "llm": (92, 102), "l3": (70.5, 86), "tools": (54.5, 65),
    "l1": (36, 48.5), "l2": (17.5, 30),
}
box(L, R, *Y["user"], "User request + trusted task scope",
    "Scope chosen through an application control (CLI flag / menu)\nand passed to the guard separately from the conversation")
box(L, R, *Y["llm"], "Local LLM assistant (Ollama, llama3.2:3b)",
    "Temperature 0, seed 42; tool-calling loop stops at a\nfinal answer or when a 7th tool call is requested")
box(L, R, *Y["l3"], "Layer 3: Tool-call authorization guard",
    "Deterministic Python rules, deny by default\nTools allowed by scope (D1 Table IV); recipients in scope\nand trusted; replies only to the mailbox-metadata sender;\n"
    "only the named file; one high-risk action per task", lw=2.4)
box(L, R, *Y["tools"], "Simulated tools on a synthetic environment",
    "read_inbox | read_document | send_email | delete_file\nin-memory inbox, files, outbox, contacts (reset every run)")
box(L, R, *Y["l1"], "Layer 1: Injection detector",
    "ProtectAI DeBERTa-v3 (as released), CPU, threshold 0.5;\nwhole output scored in 510-token windows (128 overlap);\nany window flagged: whole output quarantined", lw=2.4)
box(L, R, *Y["l2"], "Layer 2: Content isolation (delimiting)",
    "<untrusted_content source=\"email:e1\"> ... </untrusted_content>\nsystem prompt: tagged text is data, not instructions;\ndelimiter look-alikes inside content are escaped", lw=2.4)

# right-hand boxes
box(75, 100, 89, 103, "Final answer", "NOT checked by Layer 3\n(answer manipulation is\na residual risk)", style="dashed", tsize=10)
box(75, 100, 51, 68, "Attacker", "Controls only the content of\nsome synthetic emails and\ndocuments; cannot change\ncode, prompts or scope", style="dashed", tsize=10)

# ---- main flow arrows
path([(CX, Y["user"][0]), (CX, Y["llm"][1] + 0.4)])
path([(CX, Y["llm"][0]), (CX, Y["l3"][1] + 0.4)]); label(CX + 1.2, 89, "proposed tool call\n(logged before Layer 3)")
path([(CX, Y["l3"][0]), (CX, Y["tools"][1] + 0.4)]); label(CX + 1.2, 67.8, "allowed: execute")
path([(CX, Y["tools"][0]), (CX, Y["l1"][1] + 0.4)]); label(CX + 1.2, 51.5, "tool output")
path([(CX, Y["l1"][0]), (CX, Y["l2"][1] + 0.4)]); label(CX + 1.2, 33, "pass")

# loop back to the LLM (right side)
path([(R + 0.3, 23.5), (69, 23.5), (69, 95), (R + 0.4, 95)])
label(71.0, 36, "tagged data back to the model (next turn)", rot=90, ha="center", size=8.0)

# final answer
path([(R + 0.3, 99), (74.6, 99)]); label(R + 1.0, 100.8, "no tool call", size=7.8)

# attacker content enters the environment
path([(74.6, 59.5), (R + 0.4, 59.5)], ls="dashed")

# deny path (left)
path([(L - 0.3, 78), (2, 78), (2, 97), (L - 0.4, 97)], ls="dashed")
label(0.3, 86, "deny: not executed, policy message", rot=90, ha="center", size=8.0)

# quarantine path (left, outer)
path([(L - 0.3, 42), (-7, 42), (-7, 94.5), (L - 0.4, 94.5)], ls="dotted", lw=1.4)
label(-8.7, 62, "flagged: whole output withheld, quarantine notice instead", rot=90, ha="center", size=8.0)

ax.text(43, 7.5, "Every proposal, guard decision, execution, detector score and isolation step is written to one JSON-lines log per run.\n"
        "Layers 1-3 are switched independently by configuration files, giving the five evaluation configurations.",
        ha="center", va="center", fontsize=8.0)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print(f"saved {OUT}")
