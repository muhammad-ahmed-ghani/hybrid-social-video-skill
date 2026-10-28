# Pre-publish attention curves for video: state of the art and what to build

Status as of 2026-10-20. Product under study: a user uploads a finished cut (ad, reel, trailer). The system shows, second by second, where an average viewer's attention rises and drops, plus notes such as "weak hook", "weakest stretch at 0:14" and "strongest moment", so content can be tested before it is published.

Evidence levels: **V** read on the primary page or paper. **V\*** read by a research agent through a summarising fetch tool or a PDF parse, not re-checked by me. **R** reported by a secondary source. **I** inference or my own computation. Items I re-checked myself on 2026-10-20 are marked **V+**. Vendor claims are marked "vendor". No prices appear here.

## 1. Bottom line

1. **Nobody has published a per-second retention predictor that is validated against per-second human data.** Not in academia, not in the commercial tools. The nearest academic item is a single-creator study with no sample size stated and no mean-curve baseline (Husiev and Vergunova, 2026). The nearest commercial claims are Amplified AttentionAI ("second-by-second decay curves", May 2026, no accuracy figure; V+) and Neurons video (per-frame stills, and the vendor says it ignores sequence and audio; V+). Building this means doing the validation yourself, and that is also the differentiator.
2. **Three things are measurable and predictable to a degree.** (a) Early hold of a whole video: the best content-only result on the SnapUGC benchmark is SROCC 0.707 / PLCC 0.714, which leaves about half the rank variance unexplained (V+, I). (b) Replay curves, a proxy: the best model reaches Kendall tau 0.351 per video on MoSu (V+), against 0.16 to 0.17 for a content-free position prior that I reproduced (I, V+ rerun). (c) Where people look: saliency models are mature and cheap, but gaze is not retention.
3. **The position artefact decides whether a per-second result means anything.** Curves are dominated by where in the video a second falls. A July 2026 preprint found a probe at r = 0.47 that "collapses to a temporal-shape artifact"; the position-controlled partial correlation was +0.058 (95% CI [-0.04, 0.15], 48 videos; V+). Every per-second claim must be reported after removing the mean curve by position, and against loudness, motion and cut-rate baselines.
4. **Brain-encoding models are not an engine.** The strongest (TRIBE v2) is licensed CC-BY-NC-4.0, predicts a lagged, smoothed cortical average, and has no validated link to engagement (V+, V).
5. **Content alone cannot see the audience, the distribution, the thumbnail, the caption or the sound state.** The output must be framed as "relative to videos like this one on this platform", with uncertainty bands, and notes must be able to abstain.
6. **Recommended build** (section 6): cached per-second features from open encoders plus hand-built editing and audio signals, a small sequence model with a discrete-time hazard head conditioned on platform and length, multi-task pretraining on public proxy labels, then fine-tuning and calibration on first-party retention exports, conformal bands, notes computed from the curve with thresholds taken from the calibration distribution, and an LLM used only to phrase them.
7. **Licence traps:** TRIBE v2 (non-commercial), QVHighlights annotations (CC BY-NC-SA 4.0), AdsTrace (non-commercial), SnapUGC (no licence stated). MoSu (CC-BY-4.0) and Mr.HiSum labels (CC BY 4.0, plus YouTube terms) are usable.

## 2. What "attention" can mean, and which label exists

| Target | What it measures | Per-second labels available? | Verdict for this product |
|---|---|---|---|
| Retention (share still watching at t) | the thing creators care about | none public, for short videos, ads or trailers (V\*) | the right target; must come from first-party analytics |
| Hook hold, P(watch past 5 s) | early abandonment, one number per video | no; SnapUGC ECR, rank-normalised (V+) | best-validated; use as a hook head |
| Most Replayed | replay frequency in 100 segments | yes, per second after resampling | a proxy; biased at the start and self-reinforcing (V\*) |
| Gaze or saliency | where eyes go | yes, frame level | explains "where", not "whether"; no study links gaze spread to watch time (R) |
| Predicted brain response | modelled cortical BOLD | yes, but lagged by seconds | no validated link to engagement (V+) |
| Inter-subject correlation (ISC) | how much viewers' brain or gaze signals agree | needs real viewers | strongest human evidence; EEG ISC vs Super Bowl Ad Meter r = 0.81 on 20 ads (V); not predictable from content with a validated model (V) |
| Memory or recall | what viewers remember | per video | different construct |
| Per-second ad CTR | clicks per second of exposure | AdsTrace, 2,833 ads; no paper or metrics (V\*) | interesting, non-commercial licence |

## 3. State of the art by approach

### 3.1 Whole-video engagement from content (the best-measured task)

- **SnapUGC and the VQualA 2025 challenge.** 120,651 Snapchat Spotlight videos of 5 to 60 s; splits 106,192 / 6,000 / 8,459; the target ECR is "the proportion of viewers who watched the video for at least 5 seconds", released rank-normalised (V+). First place (ECNU-SJTU): final 0.710, SROCC 0.707, PLCC 0.714. Co-first IMCL-DAMO: 0.698 / 0.696 / 0.702. A text-only entry scored SROCC 0.439 / PLCC 0.444 (V+). 97 participants, 15 valid submissions (V\*).
- **Recipe that won:** fine-tune video-language models on a handful of frames, audio and title text, regress one number, and ensemble three or four models (V\*). Audio helped: VideoLLaMA2 with audio 0.691 SROCC against Qwen2.5-VL without audio 0.665, though backbones differ, so audio is not isolated (V\*). Little else mattered: 5 versus 8 frames moved SROCC by 0.005 (V\*). A frozen model with a linear head reached 0.405 (V\*).
- **Ceiling (I):** SROCC squared is about 0.50, so a realistic cross-video content-only ceiling is near 0.7 rank correlation, not 0.9.
- **Content is the weak part of popularity.** On 5.3M YouTube videos, duration alone explains more than 58% of the variance of watch percentage, and channel reputation (R2 = 0.42) beats topics (0.19) (V\*, Wu, Rizoiu and Xie, ICWSM 2018). In the SMP 2025 winner, dropping user-profile features raised MAPE from 0.1754 to 0.3010, while dropping video embeddings changed it to 0.1818 (V\*). A pre-publish tool has no uploader features, so expect lower numbers than recommender papers report.
- **Platform dependence:** the SnapUGC authors say their metrics depend on the platform's recommender (V\*). Numbers from Snapchat do not transfer unchanged to other platforms (I).

### 3.2 Replay-curve prediction (the only per-second public labels)

| Dataset | Size and label | Licence | Notes |
|---|---|---|---|
| Mr.HiSum (NeurIPS 2023) | 31,892 YouTube-8M videos, 121 to 300 s, each over 50,000 views; Most Replayed in 100 bins aligned to 1 fps | labels CC BY 4.0; features not shipped; YouTube terms apply | a 25-video user study found 64.8% of clips agreed with the label, 19.6% disagreed (V\*); the authors say at least 1,000 test videos are needed for a stable evaluation (V\*) |
| MoSu (ICLR 2026) | 52,678 videos, 120 to 501 s, CLIP, AST and RoBERTa features per second; filtered to videos with an English transcript, an audio track, over 50,000 views and at least 120 s (V+) | CC-BY-4.0, features only | the first five seconds of every label are zeroed because replay curves spike at the start and models would learn "start = important" (V+) |
| YTMR500 (ICCV-W 2023) | 500 vlog and travel videos | public | humans scored at random level (inter-rater Krippendorff alpha = -0.017); deep models barely beat random (V\*) |
| Rhapsody (2025) | 13,364 podcast episodes | audio not released | a frequency (position) baseline scores 0.224 hit against 0.220 random; zero-shot GPT-4o 0.265 (V\*) |

- **Best model:** TripleSumm (ICLR 2026) fuses visual, audio and text features per second with 1.37M parameters and 0.97 GFLOPs, MIT code. On MoSu it scores Kendall tau 0.351, Spearman 0.472, mAP50 74.72, mAP15 44.42 (V+). Baselines: CSTA tau 0.291, VASNet and PGL-SUM 0.151 (V\*). Single-modality ablations: visual 0.298, audio 0.271, text 0.267 (V+). On Mr.HiSum: tau 0.258 (V\*).
- **The baseline that matters (I, V+ rerun).** I reran the research agent's script on the released MoSu labels, 5,263 test videos, predicting each video with the training-set mean curve and no content. Normalised-position prior: tau 0.162, rho 0.223. Absolute-time prior: tau 0.173, rho 0.230. Excluding the zeroed first five seconds: 0.128 to 0.137. Random: 0.001. So a content-free prior reaches roughly half of the best model's score, and VASNet and PGL-SUM sit at or below it. Content adds real but modest signal on this proxy.
- **Why the proxy is shaky:** replays are not retention; curves are biased at the start and self-fulfilling once the UI shows them (V\*); viewers cannot guess the peaks (YTMR500). Split-half reliability of replay heatmaps is 0.82 on 48 videos, which sets a ceiling near r = 0.9 (V\*).

### 3.3 Direct attempts at a curve from content

- **Husiev and Vergunova (Artificial Intelligence, 2026 issue 1; V\*).** One creator's Minecraft videos; InternVideo2, M2D2 audio, SigLIP 2 and E5-Small features; a two-stage design (ArcFace metric loss, then a cross-modal transformer). The curve is a 100-point vector at 1% steps of duration, not seconds. MAE 0.062 against 0.089 for direct regression; XAUC 0.74 against a median-split baseline of 0.61. No sample size, no mean-curve baseline, one creator. They dropped 1080x1920 videos because auto-looping Shorts showed retention above 100%. Treat it as a design sketch.
- **AdsTrace:** per-second ad CTR for 2,833 e-commerce ads, 10.2 GB; no paper, no metric, licence conflict (CC BY-NC on the dataset card, CC BY-NC-SA on GitHub) (V\*).
- **SegMM (recommender):** predicts the 5 s segment where a user skips; the position-only baseline gets HR@1 0.2619 against 0.4072 for the full model (V\*). It confirms how strong position is even in a skip task.

### 3.4 Highlight and moment detection

- QVHighlights scores 2 s clips against a **text query**. Without a query these models cannot score an arbitrary cut. Annotations are CC BY-NC-SA 4.0; code is MIT (V\*). Best published: FlashVTG with an InternVideo2 backbone, HD mAP 44.09, HIT@1 71.01 (V\*). A training-free August 2026 preprint (REZE) reports 44.18 and 73.41 (V\*, abstract only). Features are precomputed, so compute is small.
- Query-free options exist only on the replay proxy (TripleSumm, above). AHA (NeurIPS 2025) is online and scores against a language task description (V\*).
- **Use:** as a source of ideas and pretraining signal for a "strongest moment" head, not as the engine.

### 3.5 Saliency and gaze

- **DHF1K** (eye-tracking, frame level): SalFoM leads with CC 0.5692, NSS 3.3536 (V\*, undated leaderboard).
- **NTIRE 2026** (mouse-tracking, over 5,000 viewers, 2,000 videos, audio on): winner iLearn CC 0.8280; a **centre-prior baseline already scores CC 0.4101** (V\*). A large share of saliency "accuracy" is centre bias. Mouse-tracking scores are not comparable to eye-tracking scores.
- **Turning saliency into a time curve:** ViASNet (Ye and Wedel, 28 May 2026) computes the entropy of the predicted saliency map frame by frame "as a diagnostic tool to identify ads and scenes that fail to engage viewers"; 151 ads, about 20 eye-tracked viewers each, entropy illustrated on 15 unseen ads; no outcome validation, no code (V+). Cuts raise entropy, so a raw curve shows artefacts at every cut and needs cut-aware normalisation against a centre prior (I).
- **Licences:** ViNet++ README footer says CC BY-NC-SA 4.0 (treat as non-commercial until the LICENSE file is read); most others unchecked (V\*).
- **Verdict:** a useful interpretable layer ("what is the eye pulled to, is the frame clutter-free at the hook"), and a feature for the retention model. Not the retention estimate.

### 3.6 Brain encoding and ISC

- **TRIBE** (Meta FAIR) won Algonauts 2025 with mean Pearson r 0.2146 over 1,000 cortical parcels on held-out films (V\*). **TRIBE v2** (arXiv 2605.04326, May 2026) predicts an average subject on the fsaverage5 mesh (about 20k vertices); the repository states predictions "are offset by 5 seconds in the past, in order to compensate for the hemodynamic lag"; code and weights are CC-BY-NC-4.0 (V+). Features run at 2 Hz (V\*).
- **No validated link to engagement.** Predicted-fMRI global field power against YouTube replay heatmaps: partial r = +0.058 (95% CI [-0.04, 0.15]; t(47) = 1.21, p = 0.23), "not above simple loudness/motion baselines" (V+). On video memorability the brain projection beat its own V-JEPA 2 backbone on one dataset (0.415 vs 0.368) and lost on another (0.544 vs 0.594) (V\*). Both are small preprints; peer review unchecked.
- **ISC** is the best human evidence: EEG ISC against Super Bowl Ad Meter ratings r = 0.81 on 20 ads, r = 0.51 against the sample's own ratings (V, Dmochowski 2014); a 2025 meta-analysis gives ISC-attention r = 0.65 over 14 studies (V). It needs real viewers; I found no validated way to predict ISC from content.
- **Verdict:** at most one candidate feature, and only if licensed. The memorability audit suggests the backbone alone often matches the projection.

### 3.7 Editing, audio and the first seconds

- **Shot detection:** TransNetV2 (MIT) F1 77.9 on ClipShots, 96.2 on BBC Planet Earth; AutoShot (MIT) claims +4.2% F1 on its own set; OmniShotCut (May 2026) reports F1 0.881 against 0.814 for TransNetV2 on its own 114-video bench, with no code release stated (V\*). For finished reels, TransNetV2 plus PySceneDetect is enough to get a cut rate.
- **Editing features and viewing:** shorter scenes raise attentional synchrony in eye-tracking of 42 public service announcements (JAMS, March 2026; abstract only, V\*). That is attention, not drop-off. An April 2026 preprint found an inverted U between a composite "sensation" score and engagement on Reels, with shots per second, face duration and brightness carrying 52% of model importance; retention was not measured (V\*).
- **Audio:** thin and correlational. Douyin automotive videos: loudness positive for likes and comments (V\*). edX: engagement rises with speaking rate within a length bucket, 6.9M sessions, educational video (V\*). Nothing ties silence, dead air or music onset to retention curves.
- **First seconds:** measured data are old or platform-reported. YouTube TrueView traces from 2016: 35% of skips happen in under 6 s, the mean skip comes at 20% of the ad (V\*). TikTok swipe study (NSDI 2023, 133 MTurk workers, 15,344 swipes): 29% of swipes fall in the first 20% of a video, 42% in the last 20% (V\*). Meta says "up to 47%" of campaign value is delivered in the first 3 s, with no method or date (V\*). I found no peer-reviewed test of a "3-second rule". "Hook rate" and "hold rate" are practitioner terms; no platform defines them, and hold rate has at least three formulas (R).
- **Weak-stretch detection** has no benchmark. ViASNet's entropy is the closest published idea.

## 4. The commercial market and how far to trust it

Three different products are sold under one word (V\*, vendor pages):

| Family | Examples | Output | Validation shown |
|---|---|---|---|
| Eye-tracking saliency extended to video frame by frame | Neurons, Dragonfly AI, Attention Insight | heatmaps, area-of-interest shares, per-frame scores | stills benchmarks; "accuracy" undefined |
| Panel-trained ad-effectiveness predictors | Kantar LINK AI, System1 Test Your Ad Screen (beta), DAIVID, Adverteyes (ex-Realeyes), Amplified AttentionAI, Vidmob | scores, percentiles, emotion curves, creative tags | whole-ad correlations or lift, vendor-run |
| Media-placement attention predictors | Lumen | probability an impression is viewed | not about the creative; not comparable |

- **Closest to this product:** Amplified AttentionAI (second-by-second decay curves, launched 21 May 2026; trained on "over 2 million real humans across 21 global markets"; "continuously validated"; no accuracy figure; V+), Neurons video (May 2026), DAIVID (second-by-second emotion).
- **Neurons states its video score "uses the image prediction model per frame", that "the sequential information encoded in a flow of video frames and the impact of audio are not exploited", and quotes "an accuracy of 92%" without defining it** (V+, vendor). The best-specified Neurons figure is R2 = 0.74 on 170 still images at a fixed 5 s (V\*, vendor, 2023).
- **Accuracy headlines are undefined:** Neurons 95/92/90%, Dragonfly 89%, Attention Insight 90 to 94.5%, Vidmob 83% (a 3-second view-through forecast on 443 assets), Kantar "7 in 10". None states the metric on the page read (V\*, vendor).
- **No vendor validates a second-by-second curve against second-by-second human data** (V\*). System1 itself says its beta "is designed to determine" accuracy (V\*, vendor).
- **Standards:** the IAB/MRC Attention Measurement Guidelines (November 2025) say an "unvalidated predictive model without empirical support" falls outside the guidance, and require forced or simulated exposure biases to be studied (V\*). A transparent, validated predictor would be unusual in this market.
- **Platforms:** no pre-publish predictor from Meta, TikTok, YouTube or Google was found. Their metrics are post-hoc and the hook window differs: Instagram skip rate covers the first 3 seconds (R); YouTube's retention "Intro" is the share still watching after 30 seconds, and key moments need at least 60 s and 100 views (V\*); Shorts "stayed to watch" has no published seconds threshold (V\*). A product should define its own hook window, state it, and not claim it equals a platform metric.
- **Legal:** EU AI Act Article 5(1)(f) bans inferring emotions in workplaces and education settings (V\*); facial movements are "not universally diagnostic of emotional states" (Barrett et al. 2019; V\*). Keep the product on content-level attention, not on inferring a viewer's emotions, and do not recruit employees or students as an emotion-inference validation panel in the EU (I). Panel eye-tracking and webcam data fall under GDPR (I).

## 5. Reading the evidence as design constraints

| Finding | Constraint for the build |
|---|---|
| No per-second validated retention model exists | validation is part of the product; publish the protocol |
| Position prior gets about half of the best replay model's tau | evaluate against it; predict deviation from the benchmark curve |
| Half of rank variance is unexplained even at video level | show bands, allow abstention, never imply precision |
| Replay and gaze are proxies | calibrate on real retention exports before claiming anything |
| Content cannot see audience, sound state, thumbnail, distribution | state it in the UI; offer a sound-off variant; compare to similar videos only |
| Hook window is undefined across platforms | define it in the product and report the platform-native definition next to it |
| Looping Shorts report retention above 100% | model loops explicitly or filter them from training |

## 6. Recommended architecture (my design, tagged I)

**6.1 Ingest and cached features (once per upload).**
- Decode, sample frames at 1 fps (2 fps for the first 5 s), detect shots (TransNetV2 or PySceneDetect), transcribe with word timestamps, run OCR on on-screen text, and compute audio loudness, speech and music presence, silence and onset strength. These language-neutral signals are the baseline every learned feature must beat.
- Per-second embeddings: SigLIP 2 per frame (Apache-2.0 on its model card; V\*); one video encoder over 1 to 2 s windows (V-JEPA 2 or VideoPrism; code licences are permissive, weight terms unconfirmed, so check before use; V\*); one general-audio encoder and a speech encoder (Whisper). Gemini's hosted video API samples at 1 frame per second by default and costs roughly 100 to 300 tokens per second of video (V\*), a fallback for a first version.
- Keep a full audio-visual language model (Qwen3-Omni is Apache-2.0 but needs 78.85 GB at 15 s up to 144.81 GB at 120 s, BF16 theoretical minimum; V\*) as an optional explainer, not as the feature extractor.

**6.2 Model.**
- A small transformer or GRU over the per-second feature sequence, with static covariates: platform, ad or organic, length bucket, an intended-audience descriptor, and a sound-on or sound-off flag.
- A **discrete-time hazard head** h_t with S(t) = product of (1 - h_k), monotone by construction; Kvamme and Borgan found the hazard parameterisation slightly better than the PMF one, with quantile-based discretisation preferred for small data (V\*). Add quantile outputs so each second has a band. Replays are not retention and can rise, so keep them as a separate head.
- Predict **relative** retention: the deviation from the benchmark curve for the same platform and length bucket. This removes the position artefact by construction and matches how YouTube presents retention (V\*).
- Auxiliary heads for pretraining: hook hold P(watch past 5 s) in the SnapUGC style, a replay curve (MoSu), and a per-segment highlight score. Watch-time work from recommenders (D2Q, TPM, CREAD, CQE, 2022 to 2026) transfers as target design and duration debiasing, not as user modelling (V\*).
- Transformer against state-space head: no head-to-head on frozen per-second features was found; with a few hundred to a few thousand steps a small transformer or GRU is the safe default (I).

**6.3 Data strategy.**
1. Pretrain on public proxies: MoSu (CC-BY-4.0), Mr.HiSum labels, and SnapUGC only after its licence is settled with its authors.
2. Fine-tune on first-party retention exports: customers' own analytics, with consent. This is the real label and the moat.
3. Hold out by creator and campaign, deduplicate by embedding similarity, and split by time to mimic publish-then-measure.

**6.4 Uncertainty.** Split-conformal intervals on the quantile outputs, calibrated on a creator-grouped hold-out, with coverage reported per length bucket and platform (I; the survival-band literature gives asymptotic guarantees under conditions that new creators and platforms break; V\*). Suppress a note when its band overlaps neighbouring seconds.

**6.5 Notes computed from the curve, not from a language model.**
- **Hook:** predicted hold at the product's hook window (3 s by default, shown with the platform definition next to it) against the percentile of the benchmark distribution for that platform and length. The percentile cut-offs come from the calibration set when it is built, not from constants in code.
- **Weakest stretch:** the window with the largest excess hazard over the benchmark whose band excludes zero, with a minimum width set from the video's own shot length distribution.
- **Strongest moment:** the largest relative uplift in predicted retention or replay head, reported with the shot boundary and audio onset nearest to it.
- **Why:** attribution by leave-one-second-out over cached features, then counterfactual cut-and-rescore (drop rows, re-encode only seam windows, check splice artefacts); a 2026 corpus paper finds direct scoring matches greedy removal at about 25 times fewer oracle calls (V\*).
- **Language model use:** phrase the notes from computed numbers, the transcript line and the shot list. Do not ask it to find timestamps: fine-grained temporal grounding by multimodal models is flagged unreliable (TimeLens, V\*), and text-only judges underperform video judges (VideoJudge, V\*). No validated judge for "is this attention note correct" exists, so keep a human-audited note set.

**6.6 Presentation.** A relative curve with a band, labelled "compared with videos of this length on this platform". Mark the hook window used. Show a sound-off simulation (audio features zeroed, captions on) because content cannot see how a viewer watches. Offer the optional saliency layer (where the eye goes at the hook, clutter, text size) as an explanation, not as a score.

**6.7 Cost shape (no prices).** Decoding and sampling are CPU. The per-second encoders are the only GPU-heavy step and run once. Features are small and cacheable; the head is tiny, so a counterfactual re-score costs milliseconds plus a seam re-encode. A full omni model on every upload is the expensive option.

## 7. Evaluation protocol (design, tagged I unless cited)

- **Per video:** rank correlation across seconds after subtracting the benchmark mean curve by relative position (partial correlation), hazard log-likelihood, MAE on S(t), location error of the weakest 3 s window, and hook drop in the first 3 s.
- **Baselines to beat, in order:** population mean by position; duration-conditioned mean; a regressor on loudness, motion and cut rate. The ship gate is a partial correlation whose 95% interval excludes zero against all three.
- **Across videos:** SROCC and PLCC on hook-hold, and pairwise AUC (SnapUGC uses final = 0.6 x SROCC + 0.4 x PLCC; V+).
- **Sample size:** at least 1,000 validation videos (Mr.HiSum robustness analysis; V\*).
- **Ceilings:** 0.82 split-half reliability on replay heatmaps (48 videos; V\*); none found for retention curves or human attention ratings, so measure one on your own data.
- **Leakage traps:** same creator, same campaign or template, re-uploads and trimmed versions, the same footage at different lengths, looped Shorts above 100%, and popularity-filtered datasets that exclude the cold-start tail.
- **Causal check:** real before-and-after pairs (two cuts of the same video) are the only direct test of the counterfactual notes; collect them.
- **Notes:** precision on a human-audited set, and the share of notes suppressed.

## 8. Build path

Each phase ships only if it beats the previous one on section 7.

1. **Signals and benchmark.** The ingest signals above, a benchmark curve per platform and length bucket from customer analytics, and rule-based notes against percentiles. This is the baseline everything else must beat.
2. **Learned features.** Per-second embeddings plus a shallow model on relative retention, evaluated against phase 1.
3. **Hazard sequence model** with multi-task pretraining on MoSu, Mr.HiSum and hook-hold labels, then first-party fine-tuning and conformal bands.
4. **Counterfactual editor.** Cut-and-rescore and an LLM that phrases notes; consider a language-model ensemble for hook-hold, where the SnapUGC recipe applies.

## 9. Risks and open questions

- **Ceiling:** about 0.7 rank correlation on whole-video hook hold; per-second ceilings unknown.
- **Overclaiming:** the market uses undefined accuracy headlines; a product that publishes its metric, baselines and failure cases is unusual.
- **Average-viewer bias:** optimising toward the average viewer can flatten distinctive work; keep the output advisory.
- **Not found:** a public per-second retention dataset with raw video; a duration-only or position-only baseline on SnapUGC; SnapUGC's licence and test labels; any 2026 SnapUGC follow-up; Algonauts 2026; independent validation of any commercial tool on video; a peer-reviewed test of the 3-second rule; any vendor showing intervals on a time curve; usability studies of these tools' notes; a primary source for the "sound-off share" figures; official TikTok and Meta metric definitions (pages not renderable by the fetch tool).
- **Questions to settle first:** which platforms and ad formats come first; whether customers can export retention curves (this decides the label); which licences allow the encoder weights in a commercial product (V-JEPA 2, VideoPrism, InternVideo, Dasheng and OpenBEATs weights are unconfirmed); whether the first release shows only hook and weakest stretch, where the evidence is thinnest on content alone.

## 10. Where this plugs into the video skill

The hybrid-explainer skill already ends each episode with a QC step. A predicted curve with bands fits there as an optional check on the finished master, and as the feedback loop for a series: log each published episode's real retention, compare it with the prediction, and let the series memory adapt the next hook. This file is background in the skill's references: no script or rule depends on it, and it is read only when someone asks for a pre-publish attention or retention check.

## 11. Sources

Checked by me on the primary page or file on 2026-10-20 (V+):

| Claim | URL |
|---|---|
| Position-controlled partial r +0.058, CI [-0.04, 0.15], 48 videos; r = 0.47 probe collapses; TRIBE global field power | https://arxiv.org/abs/2607.01400 (Sahu and Pandey, 1 Jul 2026) |
| SnapUGC: 120,651 videos, splits, ECR definition; table: 0.710 / 0.707 / 0.714; text-only 0.441 / 0.439 / 0.444 | https://arxiv.org/html/2509.02969v1 |
| TripleSumm on MoSu: tau 0.351, rho 0.472, mAP50 74.72, mAP15 44.42; first five seconds zeroed; MoSu filters | https://arxiv.org/pdf/2603.01169 (ICLR 2026, v1 1 Mar 2026), read from the PDF text |
| Position-only prior on MoSu labels: tau 0.162 to 0.173 | my rerun of the research agent's script on `hminjeong/TripleSumm-MoSu` labels, 5,263 test videos |
| TRIBE v2: CC-BY-NC-4.0, average subject on fsaverage5, 5 s offset | https://github.com/facebookresearch/tribev2 |
| Neurons video: per-frame image model, ignores sequence and audio, "92%" undefined | https://knowledge.neuronsinc.com/neurons-engagement-prediction |
| Amplified AttentionAI: second-by-second decay curves, 2M humans, 21 markets, no accuracy figure | https://www.advanced-television.com/2026/05/21/amplified-launches-predictive-ai/ |
| ViASNet: frame-wise entropy of predicted saliency; 151 ads, about 20 viewers, 15 unseen test ads | https://arxiv.org/abs/2605.29302 |

Read by research agents through a summarising fetch tool or a PDF parse, not re-checked by me (V\*, R):

| Claim | URL |
|---|---|
| Winner recipe, ablations, video-model comparison | https://arxiv.org/pdf/2508.02516 ; https://github.com/sunwei925/LMM-EVQA |
| SnapUGC ECCV 2024 feature ablation | https://arxiv.org/html/2410.00289v1 |
| Duration alone explains over 58% of watch-percentage variance; channel R2 0.42 | https://arxiv.org/pdf/1709.02541 |
| SMP 2025 winner ablation (MAPE 0.1754 vs 0.3010) | https://arxiv.org/html/2507.00950 |
| Mr.HiSum: 31,892 videos; user study; 1,000-video sample size | https://papers.neurips.cc/paper_files/paper/2023/file/7f880e3a325b06e3601af1384a653038-Paper-Datasets_and_Benchmarks.pdf |
| MoSu dataset, CC-BY-4.0 | https://huggingface.co/datasets/hminjeong/TripleSumm-MoSu |
| YTMR500, humans at chance | https://arxiv.org/pdf/2309.06102 |
| Rhapsody, frequency baseline | https://arxiv.org/html/2505.19429v1 |
| AdsTrace | https://huggingface.co/datasets/Xiuze/AdsTrace ; https://github.com/XiuzeZhou/AdsTrace/ |
| SegMM position baseline | https://arxiv.org/html/2504.04237 |
| Curve-from-content paper (Husiev and Vergunova) | https://jai.in.ua/archive/2026/2026-1-10.pdf |
| QVHighlights and FlashVTG | https://github.com/jayleicn/moment_detr ; https://arxiv.org/html/2412.13441v1 |
| REZE, AHA | https://arxiv.org/abs/2608.04480 ; https://arxiv.org/abs/2509.16421 |
| TransNetV2, AutoShot, OmniShotCut | https://github.com/soCzech/TransNetV2 ; https://github.com/wentaozhu/AutoShot ; https://arxiv.org/html/2604.24762v2 |
| Editing and audio studies (JAMS 2026; sensation score; Douyin; edX) | https://researchportal.bath.ac.uk/en/publications/the-dynamic-effects-of-visual-complexity-and-scene-cuts-on-viewer/ ; https://arxiv.org/html/2604.19995v1 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC10994390/ ; https://summeracademy.academic.wlu.edu/files/2020/07/Guo-et-al-2014-videos-and-student-engagement.pdf |
| First-seconds evidence (TrueView, TikTok swipes, Meta) | https://arxiv.org/pdf/1604.07890 ; https://arxiv.org/pdf/2204.12954 ; https://www.facebook.com/business/news/updated-features-for-video-ads |
| TRIBE and Algonauts 2025; memorability audit | https://arxiv.org/html/2507.22229 ; https://arxiv.org/abs/2607.16292 |
| ISC: Dmochowski 2014; meta-analysis | https://pmc.ncbi.nlm.nih.gov/articles/PMC4124862 ; https://link.springer.com/article/10.1186/s40359-025-02879-7 |
| DHF1K, NTIRE 2026 saliency | https://mmcheng.net/videosal/ ; https://arxiv.org/pdf/2604.14816 |
| Encoders and licences (SigLIP 2, VideoPrism, V-JEPA 2, Qwen3-Omni, Gemini video) | https://huggingface.co/google/siglip2-so400m-patch14-384 ; https://github.com/google-deepmind/videoprism ; https://github.com/facebookresearch/vjepa2 ; https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct ; https://ai.google.dev/gemini-api/docs/video-understanding |
| Hazard and watch-time modelling | https://arxiv.org/abs/1910.06724 ; https://arxiv.org/abs/2206.06003 ; https://arxiv.org/abs/2306.03392 ; https://arxiv.org/abs/2401.07521 ; https://arxiv.org/abs/2407.12223 |
| Conformal survival bands; judges; temporal grounding; counterfactual scoring | https://arxiv.org/abs/2505.04568 ; https://arxiv.org/abs/2509.21451 ; https://arxiv.org/abs/2512.14698 ; https://arxiv.org/abs/2610.16009 |
| Commercial claims (Neurons, Dragonfly, Attention Insight, Kantar, System1, DAIVID, Vidmob, Lumen) | https://knowledge.neuronsinc.com/how-neurons-attention-prediction ; https://dragonflyai.co/faqs ; https://attentioninsight.com/dragonfly-ai-vs-attention-insight/ ; https://www.kantar.com/inspiration/agile-market-research/can-ai-really-decode-creative-effectiveness ; https://ppc.land/system1-adds-ai-layer-to-test-your-ad-as-creative-measurement-race-heats-up/ ; https://www.exchangewire.com/blog/2026/09/21/daivid-launches-new-solution-that-analyses-thousands-of-ads-at-once-to-connect-creative-performance-to-business-results/ ; https://www.advanced-television.com/2025/08/21/study-predictive-impact-scoring-can-forecast-ad-effectiveness/ ; https://lumen-research.com/blog/lumen-releases-report-from-pwc-on-the-roi-of-attention-technology/ |
| IAB/MRC guidelines; platform definitions | https://www.iab.com/wp-content/uploads/2025/11/IAB_MRC_Attention_Measurement_Guidelines_November_2025.pdf ; https://support.google.com/youtube/answer/9314415 ; https://support.google.com/youtube/answer/12220281 ; https://www.socialmediatoday.com/news/instagram-adds-retention-insights-reels/758464/ |
| Legal and validity | https://artificialintelligenceact.eu/article/5/ ; https://www.psychologicalscience.org/publications/emotional-expressions-reconsidered-challenges-to-inferring-emotion-from-human-facial-movements.html |
