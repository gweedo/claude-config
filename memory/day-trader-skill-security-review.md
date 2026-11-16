---
name: day-trader-skill security review
description: Security review of Jakeschincariol/day-trader-skill (manual + NVIDIA SkillSpector), 2026-11-15
type: reference
---

# day-trader-skill — security review (2026-11-15)

**Subject:** https://github.com/Jakeschincariol/day-trader-skill, single commit `3d0f4ef`
("The Trader skill v2"), plugin v2.0.0, MIT. 11 skills (`trader-scanner`, `-news`, `-entry`,
`-exit`, `-timemachine`, `-budget`, `-risk`, `-broker`, `-alerts`, `-analyst`, `-pelosi`),
stdlib-only Python ≥3.8. Re-review if the repo moves past that commit.

**Verdict:** not malicious. Usable on a **paper** account with the mitigations below.

## Method

1. Manual read of all tools and SKILL.md files (code was NOT executed; the auto-mode
   classifier blocked running third-party code, which is the right default).
2. NVIDIA SkillSpector, static mode (`skillspector scan <repo> --no-llm --recursive`).
   LLM mode not run (needs an Anthropic API key).

## Facts established

- Network egress only to: `query1/query2.finance.yahoo.com`, `feeds.finance.yahoo.com`,
  `www.nasdaqtrader.com`, `www.sec.gov`, `data.sec.gov`, `disclosures-clerk.house.gov`,
  and `stooq.com` (price fallback in `trader-alerts`, **not listed in the README**).
- One subprocess: `pdftotext -layout` in `trader-pelosi/ptr.py:342` (argv list, timeout,
  no shell). No eval/exec/pickle/shell=True. No API keys read.
- All writes go under `trader/` (state, orders, plan, portfolio).
- `ticket.py` never talks to a broker; orders go through the Alpaca MCP server
  (`place_stock_order`) or the IBKR connector.

## Findings (manual), most severe first

1. **MEDIUM — order gates 1 and 2 are honor-system.** The broker flow claims three gates
   (risk PASS, typed "yes", "Allow once" card). Claude itself passes `--reply "yes"` to
   `ticket.py approve`, and `place_stock_order` never consults ticket.py state. **Only the
   permission card is enforced** — keep `mcp__alpaca__place_stock_order` under `ask`
   (never `allow`) and never run it in a permission mode that auto-approves.
2. **MEDIUM — untrusted text reaches the model unfiltered.** News headlines
   (`trader-news/news.py:459`), SEC filings and PTR PDF text are printed into context; no
   SKILL.md says to treat them as data. With #1, a crafted headline is the realistic
   steering path.
3. **MEDIUM — unpinned broker server.** Setup uses `uvx alpaca-mcp-server` with no version;
   any future PyPI release runs with the broker keys. Pin it (skill checked v2.4.0).
4. **LOW — "PAPER account" label comes from `trader/config.json` `"paper"`**
   (`ticket.py:355`), not from the broker. Verify with `get_account_info`.
5. **LOW — path built from untrusted DocID** in `ptr.py:460`
   (`os.path.join(pdf_dir, doc_id + ".pdf")`), DocID from the house.gov index. Only
   exploitable if that feed is hostile; payload must start with `%PDF`.
6. **INFO** — SEC requests send your name/email (`SEC_USER_AGENT`) to sec.gov (required by SEC).

## SkillSpector (static) result

Reported **HIGH 76/100, DO_NOT_INSTALL** — driven by false positives:

| Finding | Location | Assessment |
|---|---|---|
| CRITICAL TT3 env→network ×2 | `facts.py:112`, `news.py:183` | FP: it's `SEC_USER_AGENT` sent to sec.gov by design |
| HIGH AR2 anti-refusal | `trader-timemachine/SKILL.md:144` | FP: "Never judge a 2R plan by target-first alone" is a math rule; skill mandates a disclaimer |
| MEDIUM E1 URLs | analyst, broker | Expected: documented SEC / IBKR endpoints |
| MEDIUM AST4 subprocess | `ptr.py:342` | True, safe (pdftotext) |
| MEDIUM LP3 no allowed-tools ×11 | every SKILL.md | Informational; omitting `allowed-tools` is stricter in Claude Code |
| LOW AST7 getattr | `timemachine.py:508` | Benign (argparse) |

SkillSpector **missed** all five manual findings above (they're behavioral, not pattern-matchable).
Lesson: static skill scanners are noisy and miss agency/injection design flaws — always pair
with a manual read of the order/side-effect path.

## Mitigations if installed

- Paper account only; pin `alpaca-mcp-server==<checked version>`.
- `"permissions": {"ask": ["mcp__alpaca__place_stock_order", "mcp__alpaca__cancel_order_by_id", "mcp__alpaca__replace_order_by_id", "mcp__alpaca__close_position"]}`;
  deny options/crypto/close_all/cancel_all tools.
- Never run trader-broker from scheduled/background sessions.
- Confirm account type via `get_account_info`, not the ticket label.

## Other scanners worth knowing

`NVIDIA/SkillSpector`, `cisco-ai-defense/skill-scanner`, `snyk/agent-scan`,
`ryo-ebata/cc-audit` (skills/hooks/MCP static), `trailofbits/skills` (audit skills),
`anthropics/claude-code-security-review` (PR GitHub Action).

## Follow-up: offline backtest + Claude-driven run (2026-11-15)

Full write-up: `experiments/day-trader-backtest/RESULTS.md`.

- Harness reproduces the README TSLA trade to the cent → tool wiring trustworthy.
- **No edge on synthetic data:** README settings lose ~−0.09R/trade on bootstrapped TSLA bars
  (≈ −$521/yr on $5k); none of 27 ORB variants beats a random-entry control beyond chance.
  Caveat: bootstrap destroys intraday momentum; real contiguous history still untested.
- Time Machine over-predicted target-first (39 % predicted vs 32 % actual, n=50).
- Claude following the SKILL.md files passed 10/10 safety traps (yes-to-all, "sure", wrong
  qty, skip-risk, go-live, daily-limit block, injected headline) but disregarded the injected
  headline **silently** instead of warning the user.
- Skill bugs/quirks: `trader-news --now` treats naive times as UTC (others use NY time);
  `exit.py` default target is 2R while the README example is 1R; `news.py` prints titles only.
