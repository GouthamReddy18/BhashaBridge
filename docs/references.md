# References and technical investigation

Status below reflects an initial review of official project repositories on 2026-10-19; compatibility has not been tested locally.

## Verified repository-level facts

- AI4Bharat, [IndicLID](https://github.com/ai4bharat/IndicLID). Official README describes identification for 22 Indian languages in native and Romanized text, with English and Other classes. Its described classifier returns language classes for text; token-level predictions for mixed sentences were not verified. An adapter or separate baseline will be needed if it is sentence-level.
- AI4Bharat, [IndicXlit](https://github.com/AI4Bharat/IndicXlit). Investigation pending: verify checkpoint access, interface, license, dependencies, and Telugu Roman-to-native behavior before adoption.
- AI4Bharat, [IndicTrans2](https://github.com/AI4Bharat/IndicTrans2). Official repository describes translation for 22 scheduled Indian languages including Telugu, and lists English as a supported language. This does not establish support for Romanized Telugu?English code-mixed input. Test script expectations, model size, license, hardware, and preprocessing before use.

## Research sources to verify before citation

The initial source pass has not yet validated bibliographic metadata for foundational code-switching, Romanized normalization/transliteration, word-sense disambiguation, MT evaluation, and explainable NLP papers. Add only primary papers with checked authors, title, year, venue/DOI, and a direct URL. Do not treat repository descriptions or illustrative examples as experimental evidence.
