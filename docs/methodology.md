# Methodology

Use a versioned annotated dataset with train/development/test separation where tuning applies. Preserve original sentence, reference translation, token language labels, normalization annotations where appropriate, ambiguous spans and intended senses, notes, and split. Keep illustrative samples out of test claims.

Compare the four pipeline variants from the research question. Use BLEU and/or chrF with documented limitations, a defined human semantic-preservation rubric, token LID precision/recall/F1, ambiguity accuracy and macro-F1, plus latency and failure rate. Publish configuration, model provenance, hardware, dataset size, and scripts. Do not claim results until a reproducible run produces them.

**Current implementation boundary:** the implemented experiment runner currently supports a paired direct-versus-assisted comparison. Assisted-input categories are reported, but normalization-only, verified transliteration, and ambiguity-aware variants are not independently orchestrated as four experimental arms. A future study must extend the experiment design and artifact contract, or explicitly narrow its registered methodology, before claiming to compare all four variants. No eligible human-reviewed corpus, verified production transformation resource, real provider outputs, or human semantic ratings are available yet.
