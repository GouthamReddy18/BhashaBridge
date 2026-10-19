# Methodology

Use a versioned annotated dataset with train/development/test separation where tuning applies. Preserve original sentence, reference translation, token language labels, normalization annotations where appropriate, ambiguous spans and intended senses, notes, and split. Keep illustrative samples out of test claims.

Compare the four pipeline variants from the research question. Use BLEU and/or chrF with documented limitations, a defined human semantic-preservation rubric, token LID precision/recall/F1, ambiguity accuracy and macro-F1, plus latency and failure rate. Publish configuration, model provenance, hardware, dataset size, and scripts. Do not claim results until a reproducible run produces them.
