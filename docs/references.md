# IndicLID technical investigation

Reviewed the official AI4Bharat [IndicLID repository](https://github.com/ai4bharat/IndicLID) and README on 2026-10-19. It describes 22 Indian languages in native and Romanized scripts, with Telugu native (`tel_Telu`), Telugu Latin (`tel_Latn`), English, and Other classes. The model uses native/roman FastText branches and a pretrained language-model branch in a two-stage ensemble.

The README provides model release archives (`indiclid-ftn.zip`, `indiclid-ftr.zip`, `indiclid-bert.zip`) and links to an inference Colab notebook, but does not document a stable pip package or token-level code-mixed interface. The documented training setup installs `fasttext` and `transformers`; the repository inference code imports additional packages including PyTorch and Transformers. BhashaBridge only supports optional local FTN/FTR artifacts through FastText; it does not integrate the BERT fallback. Artifacts must be downloaded manually from official release links. No download occurs at setup or startup. The README states that code and models are MIT licensed.

The paper describes sentence-level classification and its romanized evaluation. Its romanized results are lower than native-script results; these are upstream results on its benchmark, not BhashaBridge measurements. Calling these classifiers one token at a time is an unvalidated adapter experiment, particularly for short Romanized forms and mixed text.

## Primary paper

Madhani, Yash, Mitesh M. Khapra, and Anoop Kunchukuttan. 2023. [Bhasha-Abhijnaanam: Native-script and Romanized Language Identification for 22 Indic Languages](https://aclanthology.org/2023.acl-short.71/). Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics, Volume 2: Short Papers, pages 816-826.
