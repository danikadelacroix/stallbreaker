"""Before/after Gantt chart for shop plans (rows are bays, colours are technicians)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from shopcore import clock

PALETTE = ["#4C78A8", "#59A14F", "#B279A2", "#F28E2B", "#76B7B2", "#9D755D"]


def _draw(ax, shop, jobs, plan, now, title, prev=None):
    by = {j.id: j for j in jobs}
    rows = {b.id: i for i, b in enumerate(shop.bays)}
    colour = {t.id: PALETTE[i % len(PALETTE)] for i, t in enumerate(shop.techs)}
    for jid, a in plan.assign.items():
        j = by[jid]
        late = a.end > j.due
        changed = prev is not None and jid in prev.assign and prev.assign[jid] != a and prev.assign[jid].start >= now
        ax.barh(rows[a.bay], a.end - a.start, left=a.start, height=0.62, color=colour[a.tech],
                edgecolor="#C0392B" if late else "#222222", linewidth=2.4 if late else 0.8,
                alpha=0.55 if a.end <= now else 1.0)
        label = jid.replace("RO-", "") + ("*" if changed else "")
        if late and a.end - a.start >= 50:
            label += f"\nlate {a.end - j.due}m"
        ax.text(a.start + (a.end - a.start) / 2, rows[a.bay], label, ha="center", va="center",
                fontsize=8, color="white", fontweight="bold")
    for s in plan.extra:
        if s.kind == "done":
            ax.barh(rows[s.bay], s.end - s.start, left=s.start, height=0.62, color=colour[s.tech],
                    edgecolor="#222222", linewidth=0.8, alpha=0.55)
            ax.text(s.start + (s.end - s.start) / 2, rows[s.bay], s.job.replace("RO-", ""), ha="center",
                    va="center", fontsize=8, color="white", fontweight="bold")
        else:
            ax.barh(rows[s.bay], s.end - s.start, left=s.start, height=0.62, color="#FADBD8",
                    edgecolor="#C0392B", hatch="///", linewidth=1.2)
            if s.end - s.start >= 40:
                ax.text(s.start + (s.end - s.start) / 2, rows[s.bay], "bay blocked\nwaiting for part",
                        ha="center", va="center", fontsize=7, color="#922B21")
    if now:
        ax.axvline(now, color="#C0392B", linestyle="--", linewidth=1.3)
        ax.text(now + 3, -0.62, f"now {clock(now)}", color="#C0392B", fontsize=8, va="center")
    ax.set_yticks(list(rows.values()))
    ax.set_yticklabels([f"{b.id} ({b.kind})" for b in shop.bays])
    ax.set_ylim(len(rows) - 0.4, -0.85)
    ax.set_title(title, fontsize=10, loc="left")
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.6)
    ax.set_axisbelow(True)


def gantt(shop, jobs, panels, now, path, legend_note="* = moved by the re-plan; red outline = promise time missed"):
    """panels: list of (title, plan, prev_or_None, jobs_or_None)."""
    end = max(max(a.end for a in p[1].assign.values()) for p in panels)
    xmax = max(600, ((end + 59) // 60) * 60)
    fig, axes = plt.subplots(len(panels), 1, figsize=(12, 2.5 * len(panels) + 0.9), sharex=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, p in zip(axes, panels):
        title, plan, prev = p[0], p[1], p[2]
        jj = p[3] if len(p) > 3 and p[3] is not None else jobs
        _draw(ax, shop, jj, plan, now, title, prev)
        ax.set_xlim(0, xmax)
    ticks = list(range(0, xmax + 1, 60))
    axes[-1].set_xticks(ticks)
    axes[-1].set_xticklabels([clock(t) for t in ticks])
    colour = {t.id: PALETTE[i % len(PALETTE)] for i, t in enumerate(shop.techs)}
    handles = [Patch(color=c, label=t) for t, c in colour.items()]
    fig.legend(handles=handles, loc="lower left", ncol=len(handles), fontsize=8, frameon=False)
    fig.text(0.99, 0.012, legend_note + "   |   synthetic shop data", ha="right", fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
