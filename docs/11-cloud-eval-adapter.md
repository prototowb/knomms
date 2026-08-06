# Cloud Eval Adapter — Design (Tier 4, part 2)

> Status: **proposed** (2026-08-06). The fifth Tier 4 candidate, deferred at OQ-2
> ("zero-external-cost strict; cloud adapter Tier 3 — opt-in, with explicit cost +
> privacy guardrails"). Proposed sprint: **v0.8.0 = KC-071–073**, after v0.7.0
> (`docs/10-teams-and-acls.md`).

## 1. Problem

The AI Assets pillar exists so practitioners can version prompts and eval them.
Today evals run only against local Ollama models (OQ-2), which protects the
zero-external-cost invariant but means a team building *for* a cloud model
(the common case) evals against a proxy model that doesn't behave like their
production target. The original decision anticipated this: a cloud adapter is
allowed if it is opt-in and guardrailed. This design adds one provider
(Anthropic) behind an explicit operator opt-in, without weakening the default.

## 2. Invariant preserved

**Default behaviour is byte-identical to today.** With no configuration, no cloud
code path is reachable, no cloud model is listed, and no request leaves the host.
The invariant becomes "zero external cost *unless the operator explicitly turns a
cloud provider on*" — which is what OQ-2's deferral text always said it would be.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-21 | Opt-in mechanism | `CLOUD_EVAL_ENABLED=false` (default) + `ANTHROPIC_API_KEY` in `.env`; both required for the cloud path to exist. No per-user keys | Operator-level consent matches the self-hosted model — the operator pays and owns the privacy call. Settings follow the existing `config.py` lowercase-field pattern |
| OQ-22 | Provider identity | New column `eval_runs.provider` (`'ollama'` default, Migration 015); `SubmitEvalRequest` gains optional `provider: 'ollama'\|'anthropic'` | A provider-qualified slug (`anthropic/claude…`) would break `ModelPinBadge`'s `:`-split and every bare-string call site in compose.vue. A column keeps `model_pin` clean and makes runs queryable by provider |
| OQ-23 | First provider | Anthropic only, via the Messages API. Model list fetched live from the provider's models endpoint at submit/list time — **no hardcoded model list** | One adapter proves the seam; the harness roles (`system_prompt`, `eval_suite`) map directly onto Messages API system/user turns. Live model list avoids shipping stale ids |
| OQ-24 | Pre-flight validation | `submit_eval` branches on provider: `ollama` → existing `/api/tags` check (untouched); `anthropic` → 422 if cloud eval disabled/unconfigured, 422 if model not in the provider's model list, 503 if the provider is unreachable | Mirrors the existing 422/503 contract so the frontend error mapping extends rather than forks |
| OQ-25 | Cost guardrails | `CLOUD_EVAL_MAX_CASES` (default 25): cloud runs with a larger suite are refused 422 before any spend. Per-case `input_tokens`/`output_tokens` from the API response recorded in `metrics.results[]`, with run totals in `metrics` | Bounded worst-case spend per click; visible actuals after. No price table maintained — token counts are the stable currency |
| OQ-26 | Privacy guardrail | Frontend confirm dialog before a cloud run: names the provider, the case count, and states that slot contents + eval case inputs leave the host. Recorded once per submission (no "don't ask again") | The eval payload is the user's prompt IP and test data; sending it must be a conscious act each time |
| OQ-27 | Reliability | Per-case try/except — a failed case records an error and counts as failed, the run completes; retry with backoff (3 attempts) on 429/5xx/timeouts. Applies to the local path too | Today one `generate` failure fails the whole run (`worker/eval.py:199`). Cloud rate limits would trip this constantly; fixing it for both paths is strictly better |
| OQ-28 | LLM judge | `llm_judge` cases use the run's own provider+model as judge, same as today (judge == subject) | Keeps the coupling that already exists; a separate judge-model field is future work on `grading_config` if wanted |

## 4. Schema (Migration 015)

```
eval_runs (add)
  provider   String(20) NOT NULL server_default 'ollama'
```

Backfill is the server_default itself. `downgrade()` drops the column.

## 5. Backend changes

- `config.py`: `cloud_eval_enabled: bool = False`, `anthropic_api_key: str | None = None`,
  `cloud_eval_max_cases: int = 25`.
- New `app/domains/generation/cloud.py`: thin Anthropic adapter —
  `generate(prompt, model) -> str` + usage capture, `list_models() -> list[str]`,
  retry/backoff. (Consult current Anthropic API docs at implementation time for
  endpoint shapes and model ids; do not hardcode from memory.)
- `harnesses/service.py submit_eval`: provider branch per OQ-24; stamp
  `EvalRun.provider`; case-count cap per OQ-25; pass provider to the job payload.
- `worker/eval.py`: dispatch `generate` by `run.provider`; per-case error capture
  + retries (OQ-27); token usage into `metrics`.
- New `GET /v1/eval-models`: `{providers: [{provider, models[]}]}` — Ollama tags
  plus (only when enabled) Anthropic models. Replaces the frontend's direct
  Ollama-tags BFF as the compose-page source of truth.
- `EvalRunOut` gains `provider`.

## 6. Frontend changes

- `server/api/models/index.get.ts` → proxy `/v1/eval-models`; compose.vue model
  selector becomes `<optgroup>` per provider, label "Model" instead of "Ollama
  model"; `submitEval` body gains `provider`.
- Confirm dialog (OQ-26) on cloud submissions; provider-aware error mapping
  (422 disabled/cap/unknown-model, 503 unreachable, per-case errors in the table).
- Results: token totals shown for cloud runs; run rows show a provider chip.
- `ModelPinBadge` untouched (`model_pin` stays a bare model id — OQ-22).

## 7. Non-goals

- Additional providers (the adapter seam is the deliverable; OpenAI et al. are a
  config + adapter file each, later)
- Per-user API keys, spend accounting in currency, budgets/quotas
- Cloud models for *ingestion, Q&A, curriculum, or summaries* — eval only.
  Everything else stays Ollama-local unconditionally
- Cloud judge over local subject (OQ-28)

## 8. Verification plan (live)

1. **Disabled path (default):** no `.env` changes → `/v1/eval-models` returns only
   the Ollama group; compose selector shows no cloud options; forced
   `provider=anthropic` via curl → 422; full local eval regression (KC-035 script).
2. **Enabled path** (operator key required): set `CLOUD_EVAL_ENABLED=true` +
   `ANTHROPIC_API_KEY` → cloud models listed; run the 4-case suite on the
   cheapest current model — confirm dialog appears, run completes, per-case
   tokens + totals recorded, `provider='anthropic'` on the run, SSE stream works.
3. Cap: suite with > `CLOUD_EVAL_MAX_CASES` cases → 422 before any API call.
4. Bad key → run fails gracefully with per-case errors or pre-flight 503/422,
   never a hung run.
5. Regression: pytest green, `vue-tsc` clean.

> Step 2 needs a real API key supplied by the operator at verification time; it
> is the only step that costs money (bounded by the cap and a cheap model).

## 9. Proposed ticket breakdown (v0.8.0)

| Ticket | Scope |
|---|---|
| KC-071 | Backend: Migration 015 + settings + Anthropic adapter + provider-aware `submit_eval` pre-flight + worker dispatch/retries/per-case errors/usage + `/v1/eval-models` + `EvalRunOut.provider`; unit tests (dispatch, cap, retry classification) |
| KC-072 | Frontend: eval-models BFF swap + grouped selector + provider in submit + confirm dialog + provider-aware errors + token display + provider chip |
| KC-073 | Live verification (§8), docs sync (OQ-2 note, PROJECT_STATUS, CHANGELOG), release v0.8.0 |
