#!/usr/bin/env python3
"""Generate the plan's Excalidraw diagrams.

Run:  python3 docs/diagrams/build.py
Out:  docs/diagrams/*.excalidraw  (open at https://excalidraw.com or with the VS Code
      Excalidraw extension). The diagrams are generated, not hand-edited: change this
      file and re-run.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).parent

# Excalidraw palette (background colours) used consistently:
CONTEXT = "#a5d8ff"       # pillar 1, blue
TOOLS = "#b2f2bb"         # pillar 2, green
ORCH = "#ffec99"          # pillar 3, yellow
CONTROL = "#ffc9c9"       # pillar 4, red
FEEDBACK = "#d0bfff"      # pillar 5, purple
NEUTRAL = "#e9ecef"       # grey
ACTOR = "#ffd8a8"         # orange: people and models
WHITE = "#ffffff"
TRANSPARENT = "transparent"

FONT = 1          # Virgil, hand-drawn
LINE = 1.25


class Canvas:
    def __init__(self) -> None:
        self.elements: list[dict] = []
        self.rng = random.Random(7)
        self.n = 0

    def _id(self, prefix: str) -> str:
        self.n += 1
        return f"{prefix}{self.n}"

    def _base(self, kind: str, x: float, y: float, w: float, h: float, **kw) -> dict:
        el = {
            "type": kind,
            "version": 1,
            "versionNonce": self.rng.randint(1, 2**31 - 1),
            "isDeleted": False,
            "id": self._id(kind[0]),
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "angle": 0,
            "x": x,
            "y": y,
            "strokeColor": "#1e1e1e",
            "backgroundColor": TRANSPARENT,
            "width": w,
            "height": h,
            "seed": self.rng.randint(1, 2**31 - 1),
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
        }
        el.update(kw)
        self.elements.append(el)
        return el

    # -- text ------------------------------------------------------------
    def _text_metrics(self, text: str, size: int) -> tuple[float, float]:
        lines = text.split("\n")
        w = max(len(line) for line in lines) * size * 0.55 + 8
        h = len(lines) * size * LINE
        return w, h

    def label(self, x: float, y: float, text: str, size: int = 16, align: str = "left",
              color: str = "#1e1e1e") -> dict:
        w, h = self._text_metrics(text, size)
        return self._base(
            "text", x, y, w, h,
            text=text, originalText=text, fontSize=size, fontFamily=FONT,
            textAlign=align, verticalAlign="top", baseline=size, lineHeight=LINE,
            containerId=None, autoResize=True, strokeColor=color,
        )

    # -- boxes -----------------------------------------------------------
    def box(self, x: float, y: float, w: float, h: float, text: str = "",
            bg: str = WHITE, size: int = 16, dashed: bool = False, rounded: bool = True,
            bold_first: bool = False) -> dict:
        rect = self._base(
            "rectangle", x, y, w, h,
            backgroundColor=bg,
            strokeStyle="dashed" if dashed else "solid",
            roundness={"type": 3} if rounded else None,
        )
        if text:
            tw, th = self._text_metrics(text, size)
            t = self._base(
                "text", x + (w - tw) / 2, y + (h - th) / 2, tw, th,
                text=text, originalText=text, fontSize=size, fontFamily=FONT,
                textAlign="center", verticalAlign="middle", baseline=size,
                lineHeight=LINE, containerId=rect["id"], autoResize=True,
            )
            rect["boundElements"].append({"id": t["id"], "type": "text"})
        return rect

    def frame(self, x: float, y: float, w: float, h: float, title: str,
              bg: str = TRANSPARENT) -> dict:
        rect = self._base("rectangle", x, y, w, h, backgroundColor=bg,
                          strokeStyle="dashed", roundness={"type": 3}, opacity=100)
        self.label(x + 12, y + 8, title, size=20)
        return rect

    # -- arrows ----------------------------------------------------------
    @staticmethod
    def _edge(a: dict, side: str) -> tuple[float, float]:
        cx, cy = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
        return {
            "r": (a["x"] + a["width"], cy),
            "l": (a["x"], cy),
            "t": (cx, a["y"]),
            "b": (cx, a["y"] + a["height"]),
        }[side]

    def arrow(self, a: dict, b: dict, sides: str = "rl", text: str = "",
              dashed: bool = False, via: list[tuple[float, float]] | None = None) -> dict:
        (x1, y1) = self._edge(a, sides[0])
        (x2, y2) = self._edge(b, sides[1])
        pts = [(x1, y1)] + (via or []) + [(x2, y2)]
        rel = [[px - x1, py - y1] for px, py in pts]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ar = self._base(
            "arrow", x1, y1, max(xs) - min(xs), max(ys) - min(ys),
            points=rel,
            startBinding={"elementId": a["id"], "focus": 0, "gap": 4},
            endBinding={"elementId": b["id"], "focus": 0, "gap": 4},
            startArrowhead=None, endArrowhead="arrow",
            strokeStyle="dashed" if dashed else "solid",
            roundness={"type": 2}, elbowed=False, lastCommittedPoint=None,
        )
        a["boundElements"].append({"id": ar["id"], "type": "arrow"})
        b["boundElements"].append({"id": ar["id"], "type": "arrow"})
        if text:
            tw, th = self._text_metrics(text, 14)
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            if via:
                mx, my = via[len(via) // 2]
            t = self._base(
                "text", mx - tw / 2, my - th / 2 - 10, tw, th,
                text=text, originalText=text, fontSize=14, fontFamily=FONT,
                textAlign="center", verticalAlign="middle", baseline=14,
                lineHeight=LINE, containerId=ar["id"], autoResize=True,
            )
            ar["boundElements"].append({"id": t["id"], "type": "text"})
        return ar

    def save(self, name: str) -> None:
        doc = {
            "type": "excalidraw",
            "version": 2,
            "source": "harnex docs/diagrams/build.py",
            "elements": self.elements,
            "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
            "files": {},
        }
        (OUT / f"{name}.excalidraw").write_text(json.dumps(doc, indent=1))
        print("wrote", name, len(self.elements), "elements")


# ---------------------------------------------------------------------------
def overview() -> None:
    c = Canvas()
    c.label(40, 20, "Agent = Model + Harness", size=28)
    c.label(40, 60, "The model reasons. The harness is everything around it that lets it act safely and verifiably.", size=16)

    model = c.box(40, 130, 260, 300, "MODEL\n(the brain)\n\nClaude · reasons and plans\nCodex · builds\ndecision model · decides", bg=ACTOR, size=16)

    hx, hy, hw, hh = 380, 110, 980, 560
    harness = c.frame(hx, hy, hw, hh, "HARNESS (the body) — five pillars, one directory each")

    pillars = [
        ("1 · Context & Memory\n(eyes and memory)", CONTEXT,
         "AGENTS.md (yours)\n.harnex/rules.md (rule sets)\ncanary rule\nopenspec config\nprogress conventions"),
        ("2 · Action & Tools\n(hands)", TOOLS,
         "five commands\nsetup / update skills\nprofiles (stack know-how)\nMCP: context7, markitdown,\nplaywright · Codex plugin"),
        ("3 · Orchestration\n(nervous system)", ORCH,
         "workflow: explore →\npropose → apply →\nverify → ship\nroles: architect, builder,\nverifier · decision routing"),
        ("4 · Control\n(immune system)", CONTROL,
         "permissions per role\nshell guard hook\nhuman approvals\n(commit, push, destructive)"),
        ("5 · Feedback\n(vitals)", FEEDBACK,
         "check command\nverifier (fresh context)\ncanary check hook\ndecision journal"),
    ]
    bw, gap = 180, 16
    for i, (title, bg, body) in enumerate(pillars):
        x = hx + 20 + i * (bw + gap)
        c.box(x, hy + 50, bw, 70, title, bg=bg, size=14)
        c.box(x, hy + 130, bw, 200, body, bg=WHITE, size=13)

    stated = c.box(hx + 20, hy + 360, 450, 70,
                   "A rule is STATED once (pillar 1) …", bg=CONTEXT, size=15)
    enforced = c.box(hx + 520, hy + 360, 440, 70,
                     "… and ENFORCED by a hook or a check (pillars 4, 5)", bg=CONTROL, size=15)
    c.arrow(stated, enforced, "rl")
    c.label(hx + 300, hy + 340, "the rule file names its enforcer", size=13)
    c.label(hx + 20, hy + 450, "Example: 'every answer ends with the canary word' is a rule in .harnex/rules.md\nand a Stop hook that warns when the word is missing. When it goes missing, the model has lost its instructions.", size=14)

    c.arrow(model, harness, "rl")
    c.label(300, 250, "reasons,\ndecides", size=13)
    world = c.box(1440, 330, 160, 100, "the repository,\nthe shell,\nthe browser", bg=NEUTRAL, size=14)
    c.arrow(harness, world, "rl")
    c.label(1364, 350, "acts,\nverifies", size=13)
    c.save("01-overview")


def architecture() -> None:
    c = Canvas()
    c.label(40, 20, "Where things live", size=28)
    c.label(40, 60, "One source of truth (the harnex repo), installed once on your machine, applied per project.", size=16)

    # column 1: harnex repo
    repo = c.frame(40, 120, 330, 560, "harnex repo (public)")
    r_plugin = c.box(60, 170, 290, 250,
                     "plugin/  — a Claude Code plugin\n\ncommands: explore, propose,\n  apply, verify, ship\nskills: setup, update\nagents: builder, verifier\nhooks: guard, canary\nscripts: decide, guard, setup (Python)\nprofiles: python-fastapi, react-vite\nrules: git, code, sdd, safety…",
                     bg=TOOLS, size=13)
    r_docs = c.box(60, 440, 290, 90, "docs/  plan, diagrams, decisions\nopenspec/  harnex's own specs", bg=NEUTRAL, size=13)
    c.box(60, 550, 290, 110, "Pillars are the layout inside plugin/:\ncontext · tools · orchestration ·\ncontrol · feedback", bg=WHITE, size=13, dashed=True)

    # column 2: your machine
    mach = c.frame(500, 120, 330, 560, "your machine")
    cc = c.box(520, 170, 290, 90, "Claude Code\n(desktop or terminal — your cockpit)", bg=ACTOR, size=14)
    hp = c.box(520, 280, 290, 90, "harnex plugin (user level)\ninstalled from the repo,\nupdated with one command", bg=TOOLS, size=13)
    cp = c.box(520, 390, 290, 90, "codex plugin (official)\n/codex:rescue · /codex:review", bg=TOOLS, size=13)
    cx = c.box(520, 500, 290, 70, "Codex CLI\n(installed, never driven by you)", bg=ACTOR, size=13)
    c.box(520, 590, 290, 70, "uv · OPENROUTER_API_KEY (optional)", bg=NEUTRAL, size=13)
    c.arrow(cc, hp, "bt")
    c.arrow(cc, cp, "lt", via=[(505, 215), (505, 380), (560, 380)])
    c.arrow(cp, cx, "bt")
    c.label(700, 484, "delegates", size=12)

    # column 3: a project
    proj = c.frame(960, 120, 330, 560, "a project (any stack)")
    p1 = c.box(980, 170, 290, 70, "AGENTS.md — yours, never touched\nCLAUDE.md — @AGENTS.md + rules", bg=CONTEXT, size=13)
    p2 = c.box(980, 260, 290, 90, ".harnex.yml — your choices:\nprofiles, features, canary word,\ndecision model backend", bg=CONTEXT, size=13)
    p3 = c.box(980, 370, 290, 70, ".harnex/rules.md — harness-owned,\nrendered from the rule sets you chose", bg=CONTEXT, size=13)
    p4 = c.box(980, 460, 290, 70, ".claude/settings.json — permissions\n(harness-owned)", bg=CONTROL, size=13)
    p5 = c.box(980, 550, 290, 100, "openspec/ — specs and changes\n(the commands drive it;\nyou never call openspec)", bg=ORCH, size=13)

    # column 4: services
    svc = c.frame(1420, 120, 300, 560, "services")
    dm = c.box(1440, 170, 260, 110, "decision model\n\nbackend: jev (OpenRouter)\nor mock (asks you)\nswappable", bg=ACTOR, size=13)
    mcp = c.box(1440, 310, 260, 90, "MCP servers\ncontext7 · markitdown ·\nplaywright", bg=TOOLS, size=13)
    gh = c.box(1440, 430, 260, 70, "GitHub\n(PRs, only in ship)", bg=NEUTRAL, size=13)

    c.arrow(r_plugin, hp, "rl")
    c.label(372, 300, "claude plugin\ninstall", size=12)
    c.arrow(hp, p2, "rl")
    c.label(832, 285, "/harnex:setup\n/harnex:update", size=12)
    c.arrow(hp, dm, "tt", via=[(665, 100), (1570, 100)])
    c.label(1000, 76, "route · guard (typed questions)", size=12)
    c.arrow(cx, p1, "rl", dashed=True, via=[(900, 535), (900, 205)])
    c.label(842, 440, "Codex reads\nAGENTS.md\n+ rules", size=11)
    c.save("02-architecture")


def workflow() -> None:
    c = Canvas()
    c.label(40, 20, "The workflow: five commands, one change", size=28)
    c.label(40, 60, "You run each command from Claude Code. OpenSpec works underneath and you never see it.", size=16)

    steps = [
        ("/harnex:explore", "architect (Claude, main session)",
         "understands the idea,\nlays out options,\nrecommends one", "you pick a direction"),
        ("/harnex:propose", "architect + verifier",
         "proposal, design, specs,\ntasks — verifier reviews\nthe design in a fresh context", "you approve the plan"),
        ("/harnex:apply", "builder (Codex via plugin,\nor Claude subagent)",
         "one task at a time,\ncheck command after each,\nevidence reported", "check green, scope kept"),
        ("/harnex:verify", "verifier (fresh context)",
         "diff vs specs, running app\nvia Playwright, optional\n/codex:review second opinion", "no blocking finding"),
        ("/harnex:ship", "you + main session",
         "commit (after your yes),\nPR, archive the change,\nsync specs", "you merge"),
    ]
    bw, gap, y = 240, 30, 190
    boxes = []
    for i, (cmd, role, does, exit_) in enumerate(steps):
        x = 40 + i * (bw + gap)
        top = c.box(x, y, bw, 50, cmd, bg=ORCH, size=15)
        c.box(x, y + 60, bw, 60, role, bg=ACTOR, size=12)
        c.box(x, y + 130, bw, 100, does, bg=WHITE, size=12)
        c.box(x, y + 240, bw, 50, "exit: " + exit_, bg=FEEDBACK, size=12)
        boxes.append(top)
    for a, b in zip(boxes, boxes[1:]):
        c.arrow(a, b, "rl")
    c.arrow(boxes[3], boxes[2], "bb", dashed=True,
            via=[(boxes[3]["x"] + 120, 520), (boxes[2]["x"] + 120, 520)])
    c.label(boxes[2]["x"] + 150, 496, "findings go back to apply", size=12)

    dm = c.box(40, 110, 1320, 50,
               "DECISION MODEL — before each command runs, it picks tool + model for this phase and prints:  Decision: apply → Codex · gpt-6-sol · 0.91",
               bg=ACTOR, size=13)
    for b in boxes:
        c.arrow(dm, b, "bt", dashed=True)

    guard = c.box(40, 560, 640, 70, "SHELL GUARD — before every command the agent runs:\ndeterministic rules first, decision model for the ambiguous rest, never a silent allow",
                  bg=CONTROL, size=12)
    canary = c.box(720, 560, 640, 70, "CANARY — after every answer:\nit must end with the canary word; a Stop hook warns when it is missing = instructions lost",
                   bg=FEEDBACK, size=12)
    c.label(40, 650, "Human gates: choosing a direction (explore), approving the plan (propose), any commit or push (ship), any destructive command (guard).", size=14)
    c.save("03-workflow")


def apply() -> None:
    c = Canvas()
    c.label(40, 20, "/harnex:apply — the build loop, one task at a time", size=28)

    start = c.box(40, 100, 220, 70, "read tasks.md\n(from disk, in order)", bg=ORCH, size=14)
    task = c.box(320, 100, 220, 70, "next pending task", bg=ORCH, size=14)
    route = c.box(600, 100, 240, 70, "decision model:\ntask.route → codex / claude / human", bg=ACTOR, size=13)
    codex = c.box(1000, 40, 240, 60, "Codex via /codex:rescue\n(sandboxed, own branch)", bg=TOOLS, size=13)
    claude = c.box(1000, 120, 240, 60, "Claude builder subagent\n(worktree, no commit)", bg=TOOLS, size=13)
    human = c.box(1000, 200, 240, 60, "you (credentials,\ndeploys, deletions)", bg=ACTOR, size=13)
    check = c.box(1000, 320, 240, 70, "run the project's\ncheck command", bg=FEEDBACK, size=14)
    done = c.box(600, 320, 240, 70, "task.done?\nexit code = fact\nscope check = decision model", bg=FEEDBACK, size=12)
    evidence = c.box(320, 320, 220, 70, "evidence reported:\nwhat ran, what changed", bg=WHITE, size=13)
    escalate = c.box(600, 470, 240, 70, "escalate to architect\n(rewrite task or design)", bg=CONTROL, size=13)
    retry = c.box(920, 470, 240, 70, "retry once with\nthe check output", bg=CONTROL, size=13)

    c.arrow(start, task, "rl")
    c.arrow(task, route, "rl")
    c.arrow(route, codex, "rl")
    c.arrow(route, claude, "rl")
    c.arrow(route, human, "rl")
    c.label(850, 40, "code task, high confidence", size=11)
    c.label(850, 178, "design-heavy → Claude", size=11)
    c.label(850, 246, "risky → you", size=11)
    c.arrow(codex, check, "rr", via=[(1290, 70), (1290, 355)])
    c.arrow(claude, check, "rr", via=[(1270, 150), (1270, 345)])
    c.arrow(check, done, "lr")
    c.arrow(done, evidence, "lr")
    c.label(548, 330, "accept", size=12)
    c.arrow(evidence, task, "tb", via=[(430, 280)])
    c.label(440, 270, "next task", size=12)
    c.arrow(done, retry, "bl", via=[(720, 430), (880, 430), (880, 505)])
    c.label(740, 408, "check failed", size=12)
    c.arrow(retry, check, "tb", via=[(1120, 440)])
    c.arrow(done, escalate, "bt", via=[(660, 430)])
    c.label(500, 436, "failed twice /\nout of scope", size=12)

    c.label(40, 470, "Rules the builder keeps (stated in .harnex/rules.md,\nenforced by the guard): never tick tasks.md,\nnever commit, never widen the task's scope.", size=14)
    c.label(40, 580, "Manual mode: you watch each step and can stop.\nNo unattended mode is planned.", size=14)
    c.save("04-apply")


def guard() -> None:
    c = Canvas()
    c.label(40, 20, "Shell guard — what happens before any command runs", size=28)
    c.label(40, 60, "PreToolUse hook on Bash (Claude Code). Deterministic first; the decision model only sees what the rules leave ambiguous.", size=15)

    cmd = c.box(40, 130, 220, 60, "agent wants to run\na shell command", bg=ORCH, size=14)
    parse = c.box(320, 130, 220, 60, "parse: split on ; && || |\nunparseable → ambiguous", bg=WHITE, size=12)
    allow = c.box(600, 130, 220, 60, "every part in the\nread-only allowlist?", bg=FEEDBACK, size=12)
    deny = c.box(600, 230, 220, 60, "matches a deny pattern?\nrm -rf outside cwd, force push,\nreset --hard, sudo, curl | sh", bg=CONTROL, size=11)
    ask = c.box(600, 330, 220, 60, "matches an ask pattern?\nrm in cwd, git push,\nrebase, docker, kubectl", bg=CONTROL, size=11)
    dm = c.box(600, 430, 220, 70, "decision model: guard.risk\nstate = command, cwd, branch\ntimeout 3 s, one retry", bg=ACTOR, size=11)

    o_allow = c.box(900, 130, 200, 60, "ALLOW\n(no journal)", bg=TOOLS, size=14)
    o_deny = c.box(900, 230, 200, 60, "DENY\n(journal)", bg=CONTROL, size=14)
    o_ask = c.box(900, 330, 200, 60, "ASK YOU\n(journal)", bg=ORCH, size=14)
    o_dm = c.box(900, 430, 200, 70, "P(destructive) ≥ 0.30 → ask\nP(read_only) ≥ 0.85 → allow\nelse → ask", bg=WHITE, size=11)
    o_fail = c.box(900, 530, 200, 60, "unreachable / no key /\nbackend off → ASK", bg=ORCH, size=12)

    c.arrow(cmd, parse, "rl")
    c.arrow(parse, allow, "rl")
    c.arrow(allow, o_allow, "rl", "yes")
    c.arrow(allow, deny, "bt", "no")
    c.arrow(deny, o_deny, "rl", "yes")
    c.arrow(deny, ask, "bt", "no")
    c.arrow(ask, o_ask, "rl", "yes")
    c.arrow(ask, dm, "bt", "no (residue)")
    c.arrow(dm, o_dm, "rl")
    c.arrow(dm, o_fail, "rl", dashed=True, via=[(860, 500), (860, 560)])

    c.label(40, 230, "Why this order:\n• a regex on 'rm -rf' is more reliable than\n  any model and costs nothing\n• DENY never comes from the model alone\n• the hook never fails open: any error → ASK\n• rules with enforced_by: guard feed the\n  three pattern lists", size=14)
    c.label(40, 430, "Codex side: the codex plugin runs Codex under\nits own sandbox. A Codex hook with the same\nscript is a later feature.", size=14)
    c.save("05-guard")


def roadmap() -> None:
    c = Canvas()
    c.label(40, 20, "Roadmap — one capability per change, each one you can try yourself", size=28)
    caps = [
        ("C1a · installable plugin", TOOLS,
         "catalogue + plugin.json,\nthe five pillar directories,\ndocs/smoke.md",
         "marketplace add . , install,\n/plugin → harnex is listed\nwith its version"),
        ("C1b · rule sets", CONTEXT,
         "rule file format, the six sets,\nrender_rules.py → .harnex/rules.md",
         "render --sets git,code → see\nthe file; add safety → it grows\nby exactly that set"),
        ("C1c · setup", TOOLS,
         "/harnex:setup, the templates,\nthe six project files,\nthe hash manifest",
         "run setup in a scratch project,\nread the six files; run it again\n→ nothing changes"),
        ("C1d · canary", FEEDBACK,
         "transcript spike first, then\ncanary.py + the Stop hook,\nword read from .harnex.yml",
         "ask anything → answer ends\nwith your word; delete the rule\n→ the hook warns"),
        ("C2 · explore + propose", ORCH,
         "the two architect commands,\ndecision model client\n(mock + jev backends),\nrouting line on screen",
         "run /harnex:explore 'idea',\nthen /harnex:propose →\nsee 'Decision:' and the\nartifacts appear"),
        ("C3 · apply via Codex", TOOLS,
         "spike the codex plugin first;\nbuilder role, profiles moved,\ntask loop with evidence",
         "propose a 2-task change,\nrun /harnex:apply, watch\nCodex build, check green"),
        ("C4 · shell guard", CONTROL,
         "PreToolUse hook: allowlist,\ndeny, ask, decision-model\nresidue, journal",
         "ask Claude to rm -rf /tmp/x\n→ denied; ls → silent;\ngit push → asks you"),
        ("C5 · verify + ship", FEEDBACK,
         "verifier subagent (fresh\ncontext), optional /codex:review,\ncommit after yes, PR, archive",
         "finish the C3 change end\nto end and open the PR"),
        ("C6 · update & release", NEUTRAL,
         "/harnex:update, plugin\nversioning + tags, README,\n'verified against' table,\nfirst real project migrated",
         "change a rule in harnex,\nrun update in the project,\nonly rules.md changes"),
    ]
    bw, gap = 176, 10
    boxes = []
    for i, (name, bg, delivers, try_) in enumerate(caps):
        x = 40 + i * (bw + gap)
        b = c.box(x, 100, bw, 50, name, bg=bg, size=14)
        c.box(x, 160, bw, 110, delivers, bg=WHITE, size=12)
        c.box(x, 280, bw, 130, "you try it:\n" + try_, bg=FEEDBACK, size=11)
        boxes.append(b)
    for a, b in zip(boxes, boxes[1:]):
        c.arrow(a, b, "rl")
    c.label(40, 440, "Every change also has automated tests that need no credentials: rendered-file snapshots, frontmatter validation,\nhook tests over recorded stdin payloads, a fake Codex runtime for the loop, a mock decision backend, and a\ngrep for private names. The real Codex / Claude / Jev runs are the manual checks above, recorded in docs/smoke.md.", size=14)
    c.label(40, 520, "Later, not scheduled: real-backend calibration from the decision journal, a Codex-side guard hook,\nand a separate reviewer role. No unattended mode.", size=14)
    c.save("06-roadmap")


def layout() -> None:
    c = Canvas()
    c.label(40, 20, "Repository layout — the pillars are the directories", size=28)
    c.label(40, 60, "Everything a project receives lives in plugin/, grouped by pillar. Technologies are named only in profiles/.", size=15)

    root = c.box(40, 120, 200, 50, "harnex/", bg=NEUTRAL, size=16)
    plugin = c.box(300, 120, 260, 50, "plugin/  (the Claude Code plugin)", bg=NEUTRAL, size=14)
    docs = c.box(300, 560, 260, 50, "docs/  plan, diagrams, decisions", bg=NEUTRAL, size=14)
    ospec = c.box(300, 630, 260, 50, "openspec/  harnex's own specs", bg=NEUTRAL, size=14)
    c.arrow(root, plugin, "rl")
    c.arrow(root, docs, "bl", via=[(140, 585)])
    c.arrow(root, ospec, "bl", via=[(140, 655)])

    items = [
        ("context/", CONTEXT, "rules/  git · code · sdd · safety · canary · language (one file per rule)\ntemplates/  AGENTS.md, CLAUDE.md, .harnex.yml, rules.md\nmemory.md  progress and hand-off conventions"),
        ("tools/", TOOLS, "commands/  explore propose apply verify ship\nskills/  setup, update\nmcp/  context7, markitdown, playwright\nprofiles/  python-fastapi, react-vite (stack know-how)"),
        ("orchestration/", ORCH, "workflow.md  the five phases, entry and exit criteria\nroles/  architect, builder, verifier (prompts)\nagents/  builder.md, verifier.md (Claude adapters)\ndecisions/  route.yaml, task-done.yaml (typed questions)"),
        ("control/", CONTROL, "permissions.json  per-role allowlists\nguard/  patterns.yaml, guard.py (PreToolUse hook)\napprovals.md  what always asks you"),
        ("feedback/", FEEDBACK, "check-command.md  the contract a project declares\ncanary/  canary.py (Stop hook)\njournal/  decision journal format"),
    ]
    prev = plugin
    for i, (name, bg, body) in enumerate(items):
        y = 190 + i * 74
        b = c.box(620, y, 160, 60, name, bg=bg, size=14)
        c.box(800, y, 560, 60, body, bg=WHITE, size=11)
        c.arrow(plugin, b, "bl", via=[(430, y + 30)]) if i else c.arrow(plugin, b, "rl")
    c.box(620, 570, 740, 60, "scripts/  render_rules.py (sets → rules.md), decide.py (jev | mock), setup.py, update.py — Python, uv\n.claude-plugin/plugin.json  name, version",
          bg=NEUTRAL, size=12)
    c.save("07-layout")


if __name__ == "__main__":
    overview()
    architecture()
    workflow()
    apply()
    guard()
    roadmap()
    layout()
