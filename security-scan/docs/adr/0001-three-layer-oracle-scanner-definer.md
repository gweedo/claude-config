# Three-layer split: Oracle / Scanner / Definer

The capability serves two different needs — verifying that existing artifacts are
safe (the **Scanner**), and advising which package/image to pick at design time
(the **Definer**). These are not one capability: they share only a
vulnerability-and-freshness lookup, and the Definer needs far more than that
(maintenance, license, fit), of which security is one weighted factor.

We decided to extract that shared lookup as a deep core — the **Oracle** — and
build the Scanner and Definer as separate, single-purpose consumers over it.
Fusing them into one skill was rejected: it would force a shallow, overloaded
interface where the Scanner carries selection judgment it never needs and the
Definer is tempted to pick on security alone.

The Definer **advises** (shortlist + rationale); it does not autonomously decide,
because a security-only pick makes confidently wrong infrastructure choices.
