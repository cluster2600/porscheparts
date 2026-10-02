# Literature reading addendum — 2 October 2026

This note extends the reading status in frozen `research.json`; it does not
change that registry, training examples, checkpoints or evaluation receipts.
The repeated user photograph was used to identify sources, not as scientific
evidence. Main text was read through publisher PDF extraction and arXiv HTML;
PDF screenshot requests timed out, so visual inspection is not claimed.

## Small jet engine digital twin

[Wright et al., 2023, arXiv:2312.09978v1](https://arxiv.org/html/2312.09978v1)
was read in full, beyond its previously consulted abstract. The displayed
licence is arXiv's perpetual non-exclusive licence, not CC BY. Keep this as a
reference; no article text has been imported into the training corpus.

The demonstrated NG-RC predicts thrust using delayed sensor features and
quadratic terms fitted with ridge regression. It is not an LLM trained on
papers. The experiment calibrates the thrust sensor per run and reconciles
different sampling rates. Same-run and cross-run evaluations have different
scopes. Its reported NRMSE cannot establish Porsche 993 prediction accuracy.

Section 4.1 contains an arithmetic inconsistency: one constant, eight linear
and 36 quadratic features sum to **45**, although the text gives 36 total.
Future authored exercises should check feature dimensions, chronological
splits, sensor calibration and error definitions independently of source prose.

## Internal-combustion-engine review

[Tran, Sharma and Nguyen, 2023, DOI 10.61435/jese.2023.5](https://journal.cbiore.id/index.php/jese/article/download/5/5/14)
was read through the main text and conclusion. The seven-page publisher PDF
identifies *Journal of Emerging Science and Engineering* and CC BY 4.0;
the generic title returned by the web extractor is not the journal identity.

This narrative review covers sensor integration, modelling, monitoring,
maintenance and validation challenges. It supplies context rather than a
complete executable engine model, calibrated boundary conditions or a 993
solver recipe. Authored exercises can distinguish a proposed benefit from a
measured result and require comparison against actual engine observations.
No new training examples or weights have been produced from this reading yet.

## Remaining source boundaries

- [Baird et al., SAE 2006-32-0004](https://pure.qub.ac.uk/en/publications/cfd-simulations-of-heat-transfer-from-air-cooled-engines): university metadata
  was found; full text remains unavailable in this session. No claim of
  reproducing its CFD setup is supported.
- [Fin redesign study, DOI 10.19206/CE-195440](https://www.combustion-engines.eu/Improving-heat-transfer-in-an-air-cooled-engine-by-redesigning-the-fins,195440,0,2.html):
  full-text reading and existing authored exercises were already recorded.
  Its material and cooling results do not establish the 993's OEM material
  or a measured improvement on that engine.

## Training status

Run 005 remains **148/150** on its filtered synthetic comparison, with PicoGK
**7/8**, and is not qualified. This addendum does not constitute another MLX
run. Any subsequent training needs newly authored, executable exercises and
pre-registered untouched task families; the exposed 150 cases are regressions
only. Reading a paper does not itself train or validate the model.
