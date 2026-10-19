# Dataset splits

No train, development, or evaluation split is created in Phase 4. Never use unreviewed drafts as held-out evaluation data. For a future reviewed release, group duplicate/near-duplicate sentences, paraphrases, sources, and repeated templates before assigning groups deterministically. Freeze and version the assignment algorithm and seed; do not split a group across partitions. Track review status independently from split membership and inspect source/template overlap for leakage. No evaluation scores are reported.
