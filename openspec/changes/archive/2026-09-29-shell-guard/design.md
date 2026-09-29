## Context

See `proposal.md` for why. What exists today, and what this design builds on:

- `docs/PLAN.md` §9 already fixes the guard's own contract: parse, allowlist, deny, ask,
  residue to the decision model, and that a hook failure falls back to the floor and the
  session's own permission mode — never to a blanket deny. This design does not re-decide
  any of that; it says how each piece is built.
- §8's table already fixes `guard.risk`'s shape: `Score: read_only / reversible /
  destructive`, state `command, cwd, branch, is_worktree`, rule `P(destructive) ≥ 0.30 →
  ask; P(read_only) ≥ 0.85 → allow; else ask`. `decide.py` already reserves `score` in
  `QUESTION_TYPES` and already refuses it explicitly — `_question_payload` and
  `parse_response` both raise "decide.py does not yet build a request for type `score`".
  This design fills that gap; it does not reopen whether `score` is the right type.
- Five rule files say `enforced_by: guard` today: the four `plugin/context/rules/safety/
  *.md` and `plugin/context/rules/git/commits-only-when-shipping.md` — all describe the
  mechanism this design builds, including the split between the floor (coarse, always on)
  and the guard (parses, sees more, needs a running hook). Their bodies are correct ahead
  of time and are not edited here.
- `plugin/control/floor.json` (C1c) is hand-authored today, one entry per rule, each
  carrying the rule id, and, for every `Bash(...)` entry it carries, `list: "ask"` — it
  holds no `deny`-severity entry for a shell command, only for reading a credential file
  directly. C3's design note recorded that `apply` and the guard must never state the same
  fact two different ways; the floor and the guard's own patterns are that fact for these
  five rules.
- `decide.py`'s question-file format is flat `key: value` plus a bare `---`, with
  `option.<name>` collecting into a map (decision 15's YAML-*shaped* convention, reused
  by every question file so far). `rule_threshold_low` is already type-conditional —
  required for `noul`, forbidden for `choice` — so a field required only for some types is
  an established pattern, not a new one.
- `default_decisions_dir()` in `decide.py` is `plugin/orchestration/decisions/`, but
  `load_question` takes a `decisions_dir` parameter and the CLI exposes
  `--decisions-dir`. §8 places `guard.risk`'s own file at `plugin/control/guard/`, not
  alongside the routing questions — the guard's own call passes that directory explicitly;
  nothing about `decide.py`'s default changes.

## Goals / Non-Goals

**Goals:**

- A command is classified the same way regardless of which session or subagent runs it,
  except where a role's own list says otherwise.
- Every failure mode — backend down, hook crashed, output malformed — resolves toward
  asking, never toward silently allowing, and the floor still holds when the guard does
  not run at all.
- The floor and the guard read one pattern source; nothing about a rule's coverage can be
  true in one and false in the other.
- `guard.risk`'s three named probabilities stay independent (not a single "pick the
  highest" like `choice`), because "how destructive" and "how read-only" are not the same
  axis and a command can score low on both.

**Non-Goals:**

- A full POSIX shell parser. The guard treats anything it cannot confidently split as
  residue (ambiguous), never as allow; getting cleverer about parsing is later work, not
  a correctness requirement now (§9 already accepts the floor covering what escapes it).
- Detecting every `find -exec`/`-delete` spelling, every wrapper, every encoding of a
  known-bad command, or naming a new command diagram 05 illustrates but no rule states
  today (`docker`, `kubectl`, `curl | sh`) — `patterns.yaml` v1 is seeded from exactly
  what `floor.json` already commits to, entries and `guard_only` alike; growing coverage
  from observed traffic, including these, is later work (§11).
- Introducing a `deny`-severity pattern for a shell command on the **default** list — the
  one every session and every role starts from. No rule asks for one today — every
  `Bash(...)` entry `floor.json` carries is `list: "ask"`; `deny` exists only for reading a
  credential file directly. Diagram 05's deny-box examples that go beyond this (`rm -rf`
  outside cwd, a force push, `sudo`, `git reset --hard` as deny rather than ask) are the
  mechanism's own illustration of what a future deny-severity default rule could look like,
  not a claim that one exists yet; `patterns.yaml` v1 does not add one to the default list
  on its own judgement. This does not bear on D5's builder-only `deny` additions — those
  are role-scoped, never floor-expressible, and exist because §4's role matrix asks for the
  builder specifically to be *more* restricted than the default list, not because the
  default severity changed.
- A Codex-side guard, or anything about Codex's own sandbox — S1 and §9 already settle
  that as later, not v0.1.
- Changing `choice` or `noul`'s existing behaviour in `decide.py`. `score` is additive.

## Decisions

### D1 · Command classification: split first, name second, never guess past a doubt

`guard.py` splits a command on top-level `;`, `&&`, `||`, `|` (not inside quotes) using
`shlex` (standard library, decision 15) to tokenize each segment. A segment `shlex` cannot
tokenize (unbalanced quotes, a trailing backslash) — or a segment containing `` ` `` or
unescaped `$(` — makes the whole command **ambiguous**: it skips allow/deny/ask matching
entirely and goes straight to the residue path. This is deliberately conservative: a
command clever enough to defeat the splitter is exactly the kind that should not be
silently allowed, and "ambiguous → residue → decision model or ask" is still a decision,
never a bypass.

Each successfully split segment is matched, in order, against three pattern lists:
allowlist, deny, ask — the same glob-and-prefix syntax `floor.json` already uses
(`Bash(git push *)`). All of allow: every segment matches the allowlist. Any one deny
match: deny, with that pattern's rule named. Failing that, any one ask match: ask. Nothing
left over: residue, to `guard.risk`.

The whole classification pipeline — splitting, tokenizing, and matching against the three
pattern lists — runs inside one `try`/`except Exception`. Anything it raises that is not
already handled as "ambiguous" (a bug in the matcher, a malformed `patterns.yaml` entry
discovered only at match time, an unexpected exception type) resolves to **ask**, the same
outcome as an ask-pattern match, and is journalled with `source: internal_error` and the
exception's own message (D6) — distinct from a `guard.risk` backend failure, which is a
failure *after* classification succeeded, not during it. This is the same guarantee §9
already states for the script as a whole ("the guard never allows on its own error"),
applied to the classification stage specifically rather than only the decision-model call.

**Alternative considered:** shell out to `bash -n` or a real parser for a byte-exact AST.
Rejected — a new dependency and a subprocess per command where decision 15 already rules
out anything beyond the standard library for a script on the hot path of every tool call;
the conservative "ambiguous on doubt" fallback gets the same safety property without it.

### D2 · One pattern source: `patterns.yaml` generates both the guard's lists and the floor

`plugin/control/guard/patterns.yaml` is the single committed source: one list per rule id,
each entry typed `allow` / `ask` / `deny`, carrying its own `floor: yes` or `floor: no`
flag — `no` for a pattern the host's permission syntax cannot express (a wrapper, an
absolute path, anything needing the guard's own parse) — and an optional `pattern`. When
`pattern` is present, the entry is a real thing `guard.py` matches commands against, and
`floor` only decides which array the generator below writes it into, `floor: yes` or
`floor: no` alike, never whether the guard itself acts on it. When `pattern` is absent, the
entry is a **note**: it carries `rule` and `why` only, matches nothing, and exists solely
so the generator can reproduce a `guard_only` reason `floor.json` already commits to that
does not name a specific command — see below for which ones these are and why they have no
pattern to give.

**v1's content is exactly today's committed `floor.json`, transcribed** — every `entries`
row becomes a `floor: yes` entry with that row's own `pattern`; every `guard_only` row
becomes a `floor: no` entry, same rule id, same `list` value (`ask` throughout, per the
Non-Goals above) where it names one; plus a read-only allowlist (`ls`, `cat`, `git status`,
`git diff`, `git log`, …) that has no floor counterpart at all today and so is `floor: no`
throughout, each with a real `pattern`. Diagram 05's own illustrative examples beyond this
(`docker`, `kubectl`, a deny-severity `sudo` or `reset --hard`) are not transcribed — see
the Non-Goals entries above for why not, and §11 for where that growth belongs instead.

`floor.json`'s six `guard_only` reasons split unevenly here, since `floor.json`'s own
`guard_only` rows were never more than `rule` and `why` — no pattern, in that file, today.
One of the six *does* have a concrete pattern the floor's glob syntax cannot safely isolate
from an ordinary `find`: its own `-delete`/`-exec` options. That one becomes a real
`floor: no` entry with a pattern (`Bash(find * -delete*)`, `Bash(find * -exec*)`) and
`guard.py` matches it like any other ask entry. The other five — all four rows tagged
`destructive-commands-ask` (an unlisted absolute path, an environment runner, an exec
wrapper, and "whether a command is destructive often depends on the task") plus the one
row tagged `credentials-never-leave-the-machine` (the credential-intent reason) — name a
*capability* of the guard's own classification, not a command: resolving a program
reached by an absolute path or recursing into a wrapper is D1's own splitting behaviour,
not a pattern to list; telling a task-scoped deletion or a credential's intent from
anything else needs `guard.risk` or a component that knows the task, exactly what "residue
falls through to the decision model" (D1) already means. Those five stay pattern-less
notes: `rule` and `why`, matching nothing, carried only so `generate_floor.py` can
reproduce their `floor.json` rows.

A generation script — `plugin/control/guard/generate_floor.py` — reads `patterns.yaml` and
writes `plugin/control/floor.json` exactly as `floor.json` is shaped today: every `floor:
yes` entry becomes a `floor.json` `entries` row (`rule`, `list`, `pattern`  — the `floor`
flag itself is dropped, since `entries` never carried one); every `floor: no` entry becomes
a `guard_only` row carrying `rule` and `why` alone, whether or not that entry has a
`pattern` — `guard_only`'s own format has never had one, so a note and a matched `floor:
no` entry look identical once written there. Nothing about `floor.json`'s committed shape
changes.

Neither setup nor any runtime component calls `generate_floor.py`. `guard.py` reads
`patterns.yaml` directly at classification time and never reads `floor.json`; setup (C1c)
still merges the *committed* `floor.json` into a project's `.claude/settings.json` by
entry, exactly as before this design. The generator is a maintainer step — run by hand
after editing `patterns.yaml`, the same way `docs/diagrams/build.py` is — proved correct by
the regeneration check below rather than by anything invoking it in production.

A regeneration check (`uv run --with pytest pytest`, per `AGENTS.md`) runs the generator
into a temp file and diffs it byte-for-byte against the committed `floor.json` — the same
shape of check C1d used to walk hook-to-rule, applied here to floor-to-patterns. A
`patterns.yaml` edit that is not followed by re-running the generator fails this check, so
`floor.json` cannot go stale silently.

**Alternative considered:** keep `floor.json` hand-authored and add a *second*, separate
check that only compares rule coverage (every `guard`-enforced rule has a floor entry)
without a shared source file. Rejected — that check already exists (`permission-floor`'s
"every statement is covered" requirement, from C1c) and it did not stop the floor and the
guard's own lists from being two independently-edited files; only generating one from the
other removes the chance to edit just one of them.

### D3 · `decide.py` gains the `score` type: per-option thresholds, not one shared rule

A `score` question declares its named options the same way `choice` does
(`option.read_only: …`, `option.reversible: …`, `option.destructive: …`), but instead of
one `rule_threshold` shared across every option (`choice`'s "highest ≥ 0.70"), it declares
a threshold **per option that can resolve the question on its own**:
`rule_threshold.<option-name>: <value>`, an extension of the same dotted-key convention
`option.*` already uses. `rule_threshold` (the flat field) becomes required only for
`choice` and `noul`; `score` instead requires at least one `rule_threshold.<name>` and
forbids the flat `rule_threshold` and `rule_threshold_low`, the same type-conditional
pattern `rule_threshold_low` already follows for `noul`.

The response for `score` is read as one independent probability per declared option (not
a single-vector softmax like `choice`, where probabilities sum to one) — `guard.risk`'s
own rule needs `read_only` and `destructive` to be able to both score low on the same
command, which a shared-distribution type cannot represent. Resolution: options are
checked in the order the file declares them; the first whose own probability is at or
above its `rule_threshold.<name>` resolves the question to that option, carrying every
option's probability. None crossing its threshold: unresolved, same shape as any other
unresolved call. `guard-risk.yaml` declares `destructive` before `read_only` before
`reversible`, so a command that improbably scores high on both `destructive` and
`read_only` resolves to `destructive` — erring toward a question over a silent allow,
consistent with "deny never comes from the model alone" not extending to "allow may
misfire freely" either.

`reversible` declares no `rule_threshold.reversible` (§8's rule names only `destructive`
and `read_only`), so it can never resolve the question on its own — every command lands on
`destructive`, `read_only`, or unresolved. `guard.py`'s own mapping (D4) still names
`reversible` alongside `destructive` and unresolved as an ask outcome deliberately: if a
later question revision ever adds a threshold for it, the mapping needs no change, since
"anything but `read_only`" already covers it.

`decide.py` itself stays policy-free: it resolves a **named option**, never "allow" or
"ask" — those words belong to `guard.py`'s own mapping (`read_only` resolved → allow;
`destructive`, `reversible` resolved, or unresolved → ask), exactly the separation §9
already draws between the decision model judging risk and the guard deciding what to do
about it.

**Alternative considered:** reuse `noul` with `option.true` = read-only,
`rule_threshold_low` repurposed as the destructive cutoff. Rejected — `noul` resolving
`false` is a real resolved outcome elsewhere (`task.scope`'s out-of-scope), and letting
`guard.py` special-case "a `noul` resolving false is not a synonym for deny, just for
ask" is exactly the kind of caller-side reinterpretation `score` as its own type avoids
needing.

### D4 · `guard.py`'s own call to `decide.py`

`guard.py` shells out to `decide.py ask --question guard.risk --decisions-dir
plugin/control/guard/ --state -` (state on stdin, the same contract every other caller
uses), never imports `decide.py` as a module — matching how `apply_loop.py` already calls
it (C3) rather than the two scripts sharing process state. State is exactly `{"command":
…, "cwd": …, "branch": …, "is_worktree": …}`, four scalars, none of them a list, so the
D-notes in §8 about keying state by position never apply here.

### D5 · Per-role lists: an override, not a parallel format

`patterns.yaml` carries one default set of allow/ask/deny entries and, keyed by
`agent_type`, a per-role list of *additional* entries only — never a replacement of the
default list. After the read-only allowlist check, a role's own command is checked against
both the default deny/ask lists and its role's additions; any deny match wins over an ask
match regardless of list order, preferring the role match's reason when both deny. This
means a role can only be **more** restricted than the main session, never less — a
role-specific `allow` entry is rejected at load time as a format error, since the main
session's own list already governs what is safe by default and a role loosening it would
need to be a change to that shared list, visible to every caller, not a quiet per-role
exception.

### D6 · The guard's own journal

`.harnex/state/guard/journal.jsonl`, one line per deny or ask decision (never allow, per
the spec): `command`, `agent_type`, `outcome` (`deny` / `ask`), `source` (`pattern`,
`guard.risk`, or `internal_error` — D1's own exception-during-classification path), the
matched pattern, the decision's resolved option and probabilities, or the exception's own
message (whichever `source` applies), and a timestamp. Distinct from `decide.py`'s own
`.harnex/state/journal.jsonl` (every decision-model call, C2) — the guard's journal also
records deterministic pattern decisions and internal errors, neither of which ever touch
`decide.py`.

### D7 · The hook itself

`PreToolUse`, matcher `Bash`, in `plugin/hooks/hooks.json`, `uv run --quiet
"${CLAUDE_PLUGIN_ROOT}/control/guard/guard.py"`, timeout set above the script's own budget
(3 s plus one retry, per §9) with headroom the same way the canary's `Stop` hook already
budgets 5 s over its own ~1 s (C1d) — a fixed multiple, not a new number picked freely.

## Risks / Trade-offs

- **A pattern list that is merely long enough to feel complete, but is not.** →
  `floor.json`'s existing `guard_only` section is the seed list; the test suite pins every
  row of diagram 05's table as a fixture, so a gap is a missing fixture, not a missing
  feeling.
- **`shlex`-based splitting misclassifies a command that is valid but unusual shell
  syntax** (a heredoc, an unusual quoting style) → misclassification here means
  "ambiguous," which still reaches a decision, never a silent allow; the cost is an
  occasional unnecessary ask, not an unsafe allow.
- **The per-option `score` threshold order (D3) is a new, project-specific convention**
  nothing else in `decide.py` needed before → documented in the question-file format
  itself (mirroring how `noul`'s two-threshold shape is documented in `task-scope.yaml`'s
  own body) so a future question author does not have to read this design doc to use it.

## Migration Plan

- `floor.json` stops being hand-edited the moment `patterns.yaml` and the generator land;
  the first generation must reproduce the current file byte-for-byte (the regeneration
  check in D2 is this change's own proof, not just future protection).
- No installed project is affected until it re-runs `/harnex:update` (C6, not yet built);
  this change only affects the plugin's own checkout and what a fresh `setup` writes from
  here on.

## Open Questions

- Exact allow/ask/deny pattern coverage beyond what `floor.json`'s current entries and
  `guard_only` notes already name — filled in as `patterns.yaml` is written in `tasks.md`,
  cross-checked against diagram 05's own examples (`rm -rf outside cwd`, `git push`,
  `docker`, `kubectl`, …); does not change this design's shape either way.
