# Prediction Market Event-Time Study
项目简历与面试讲解包

For resume bullets, interview scripts, and full project understanding
适用于简历、面试自我介绍与项目问答

GitHub: https://github.com/JosephHuaimin/prediction-market-event-time

## 项目核心问题

As resolution approaches, do prediction market prices become more accurate and separate more cleanly by eventual outcome?

随着市场接近结算，预测市场价格是否：
- 更接近最终真实结果
- 更清楚地区分 eventual Yes 和 eventual No

## 核心结果

- Stratified sample = `600` markets.
- Matched markets by horizon = `166 / 279 / 295 / 447`.
- Brier score improves from `0.1854` at `1d before close` to `0.0615` at `last pre-close`.
- Average implied probabilities for eventual Yes vs No separate from `0.56 vs 0.31` at `1d before close` to `0.88 vs 0.13` at `last pre-close`.
- A robustness check that caps the last-preclose gap at `24h` or `6h` produces very similar results, so the headline finding is not driven by a few stale-candle outliers.

## 一、简历 Bullet Points（中英双语）

建议项目名：
Prediction Market Event-Time Study / 预测市场事件时间价格演化研究

### English Resume Version

- Built a Python research pipeline to study how prediction-market probabilities evolve as markets approach resolution using public Kalshi metadata and candlestick data.
- Constructed a metadata universe of `5.68M` unique markets, filtered to resolved binary Yes/No markets, and drew a stratified sample of `600` markets by resolution month and liquidity bucket.
- Downloaded hourly candlesticks only for sampled tickers, aligned markets in event time, and extracted implied probabilities at `1d`, `6h`, `1h`, and `last pre-close`.
- Evaluated forecast quality with Brier score, MAE, average probability paths by eventual outcome, and coarse-bin near-close calibration; found Brier score improvement from `0.1854` to `0.0615` and strong Yes/No path separation near close.
- Diagnosed sample-construction and stale-candle edge cases, then added unique-market accounting and last-preclose gap sensitivity checks to validate robustness.

### 中文版简历 Version

- 用 Python 搭建预测市场事件时间研究流程，基于 Kalshi 公开 metadata 和 candlestick 数据研究市场在接近结算时价格如何演化。
- 先建立包含 `5.68M` 个唯一市场的 metadata universe，筛选已结算二元 Yes/No 市场，再按 resolution month 和 liquidity bucket 分层抽样 `600` 个市场。
- 只对样本 ticker 下载小时级 candlesticks，并在事件时间上对齐市场，提取 `close 前 1 天 / 6 小时 / 1 小时 / 最后一个 pre-close` 四个时点的隐含概率。
- 使用 Brier score、MAE、按最终结果分组的平均概率路径和 near-close 粗分桶校准分析；结果显示 Brier score 从 `0.1854` 降到 `0.0615`，Yes/No 路径在接近结算时明显分离。
- 对样本构造口径和 stale-candle 边界问题做了专门诊断，并加入 unique market accounting 和 last-preclose gap sensitivity 检查来验证结果稳健性。

### Short Quant-Style Version

- Studied how prediction-market probabilities evolve in event time as markets approach resolution.
- Designed a stratified-sampling and event-time-alignment pipeline instead of downloading the full candle universe.
- Measured horizon-by-horizon forecast quality using Brier score, MAE, and outcome-conditioned price paths, with explicit data-quality and robustness checks.

## 二、面试介绍话术（中英双语）

### 30 秒英文版

I built an event-time research project to study whether prediction-market prices become more informative as resolution approaches. Instead of evaluating one static snapshot, I first built a metadata universe, then drew a stratified sample of 600 resolved binary markets, downloaded hourly candlesticks only for those tickers, and extracted implied probabilities at fixed horizons before close. The main result is that Brier score improves materially near close, from 0.1854 at one day before close to 0.0615 at the final pre-close observation, while eventual Yes and No markets separate much more clearly in their probability paths.

### 30 秒中文版

我做了一个 event-time research project，研究预测市场在接近结算时价格是否会变得更有信息量。和只看一个静态时点不同，我先建立 metadata universe，再分层抽样 600 个已结算二元市场，只对这些 ticker 下载小时级 candlesticks，然后提取结算前固定时点的隐含概率。核心结果是：Brier score 在接近 close 时明显下降，从前一天的 0.1854 降到最后一个 pre-close 的 0.0615，同时 eventual Yes 和 eventual No 的概率路径也明显拉开。

### 90 秒英文版

This project grew out of a limitation in my first calibration study. In that first project, I learned that static calibration is useful, but it does not fully answer how information gets incorporated into market prices over time. So for the second project, I defined a more market-microstructure-style question: as resolution approaches, do prediction-market prices become more accurate and separate more cleanly by eventual outcome?

To keep the project statistically interpretable and engineering-feasible, I did not download every candle in the exchange. I first built a metadata-only universe over a fixed window from April 1, 2025 to March 31, 2026. Then I filtered to resolved binary Yes/No markets with usable timestamps and drew a stratified sample of 600 markets by resolution month and liquidity bucket. After that, I downloaded hourly candlesticks only for the sampled tickers and aligned each market in event time. For each ticker, I extracted the nearest available implied probability at one day, six hours, one hour, and the last pre-close observation.

I then evaluated forecast quality with Brier score, MAE, average probability paths by eventual outcome, and a coarse-bin calibration figure near close. The main result is that Brier score improves substantially as the market approaches resolution, and eventual Yes versus No markets separate much more clearly in the final hours. I also added explicit data-quality checks, including unique-market sample accounting and a sensitivity analysis for stale last-preclose candles, to make sure the result was not being driven by data-construction artifacts.

### 90 秒中文版

这个项目其实是从我第一个 calibration 项目的局限里长出来的。第一个项目告诉我：静态校准分析有价值，但它并不能完整回答“信息是怎么被逐步吸收到市场价格里的”。所以第二个项目我把研究问题定义成一个更像 market microstructure 的问题：随着市场接近结算，预测市场价格是否会变得更准确，并且更清楚地区分 eventual Yes 和 eventual No？

为了让项目既有统计解释性、又不至于工程失控，我没有再去抓全库 candles。第一步我先在固定时间窗 `2025-04-01` 到 `2026-03-31` 上建立 metadata-only universe。然后筛选已结算、二元、结果明确为 Yes/No、并且时间字段可用的市场，再按照 resolution month 和 liquidity bucket 做 `600` 个市场的分层抽样。之后我只对这些样本 ticker 下载小时级 candlesticks，并把每个市场放到事件时间坐标里。对每个 ticker，我提取 close 前 `1 天 / 6 小时 / 1 小时 / 最后一个 pre-close` 这四个时点最接近的隐含概率。

分析时我用了 Brier score、MAE、按最终结果分组的平均概率路径，以及 near-close 的粗分桶 calibration 图。主要结果是：随着市场接近结算，Brier score 明显下降，而 eventual Yes 和 eventual No 的概率路径在最后几个小时明显分离。为了确保这个结果不是数据构造造成的错觉，我还专门做了 unique market sample accounting 和 stale last-preclose candle 的 sensitivity analysis，验证核心结果并不是被少数异常点撑出来的。

## 三、核心图表

### Brier Score vs Time-to-Close

Figure 1. Forecast error declines materially as the market approaches resolution.

### Average Probability Path by Eventual Outcome

Figure 2. Eventual Yes and eventual No markets separate more clearly in the final hours before close.

### Coarse-Bin Last Pre-Close Calibration

Figure 3. Near close, extreme-probability bins look directionally well aligned with realized outcomes, while the middle range is less cleanly calibrated.

## 四、全篇讲解：这个研究是怎么想到的、怎么一步步落实的

### 1. 这个研究是怎么想到的？

它不是凭空冒出来的，而是从第一个项目自然升级出来的。

第一个项目回答的是一个静态问题：
“市场给出的概率和最终发生频率是否匹配？”

第二个项目再往前走一步，问的是一个动态问题：
“随着接近结算，市场价格是不是越来越有信息量？”

这个问题更像 quant interview 里会被喜欢的研究问题，因为它同时涉及：
- event-time alignment
- probabilistic evaluation
- price path analysis
- information incorporation

### 2. 为什么先做 metadata universe，而不是先抓 candles？

因为 universe 定义本身就是研究设计的一部分。

如果不先定义 universe、时间窗和样本规则，后面抓到的样本就只是 convenience sample，而不是设计出来的 research sample。metadata 的作用主要是：
- 定义总体
- 做筛选
- 建立 sampling frame
- 先控制工程规模

### 3. 为什么只保留 resolved binary Yes/No markets？

因为这个项目最终要评估的是概率预测质量。只有 resolved binary 市场才能自然映射成：
- Yes = 1
- No = 0

这样 Brier score、MAE 和 calibration 才有直接解释。

### 4. 为什么要做分层随机抽样，而不是直接取最活跃的市场？

如果只取最活跃市场，结果很容易被质疑：
- 是不是只代表最热门的市场？
- 是不是只集中在某几个月？

所以我用了 resolution month × liquidity bucket 的分层抽样。这样做的好处是：
- 月份维度更均衡
- 热门 / 冷门市场不会严重失衡
- 面试时你可以明确讲清楚样本是设计出来的，而不是随手抓出来的

### 5. 为什么只抽 600 个市场？

这是一个刻意控制工程规模的决定。

如果我直接对全 universe 抓 candles，项目会立刻变成基础设施问题，而不是研究问题。600 个样本已经足够支持：
- horizon-by-horizon metrics
- path separation
- near-close calibration
- 一定程度的 robustness

同时下载量仍然可控、可复现。

### 6. 为什么选这四个时点？

我选的是：
- `1d_before_close`
- `6h_before_close`
- `1h_before_close`
- `last_preclose`

这样做的原因是：
- 这四个点足够回答“越靠近 close 是否越准确”的主问题
- 它们容易解释
- 不会因为时间点太多把样本切得太碎

### 7. 概率是怎么从 candlesticks 里取出来的？

对每个 ticker、每个目标时点，我取“最接近目标时点的那根 candle”。

为了避免离得太远，我给前三个时点设置了容忍窗口：
- 1 day：`±6h`
- 6 hours：`±2h`
- 1 hour：`±30min`

如果超出容忍范围，就记成 missing。

对于 `last_preclose`，我取的是 close 之前最后一根可用 candle，然后再额外做 sensitivity analysis，检验这个定义是否会被少数 stale candles 扭曲。

### 8. 这个项目中间遇到了哪些真正重要的困难？

#### 困难 1：很容易重新掉进“全量抓所有 candles”的坑

我在第一个项目里已经吃过这个亏，所以第二个项目一开始就反过来设计：
- 先建 universe
- 再抽样
- 最后只抓 sampled tickers 的 candles

这是这个项目最重要的工程改进之一。

#### 困难 2：sample construction 的数字一开始不够严谨

最开始 repo 里有一个很容易被追问的点：README 里的 count 看起来像是分页处理量，而不一定像 unique markets。这个问题不是表述小瑕疵，而是会影响整个研究叙事的可信度。

我是怎么发现的？
- 通过对 README 数字形状做检查，发现前几步都是五百多万量级，到 valid-time filter 才突然掉到几十万
- 这非常像“内部处理量”而不是“研究样本量”

我是怎么解决的？
- 在 metadata build 阶段显式追踪 unique tickers
- 把 sample construction 全部改成 unique market counts
- 把 `Unique markets pulled from metadata` 正式接进最终样本构造表

#### 困难 3：有 1 个 edge-case market 是通过 settlement_ts 进窗口的

这次复跑和 QC 里，我发现了一个非常具体的边界问题：
- 有 1 个 market 的 `close_time` 在 `2025-03-30`
- 但它的 `settlement_ts` 在 `2025-04-01`

因此它会进入 metadata universe，但不应该进入 event-time sample frame。

我是怎么解决的？
- 保留它在 universe 层面的存在，因为它确实满足 metadata window 规则
- 但在 valid-time event-time sample frame 中，用 `close_time` 再收紧一次，确保真正用于 event-time alignment 的样本是 `317,071`

#### 困难 4：last-preclose 里存在少数 stale candles

QC 的时候我发现：
- `last_preclose` 最大 gap 到 close 有 6,642,181 秒，约 77 天

这说明少数市场的最后一根可用 candle 离结算非常远。

我是怎么发现的？
- 单独把 `time_diff_seconds` 的分布拉出来看
- 再把最差的几个 ticker 单独列出来

我是怎么解决的？
- 没有直接硬删，而是先做 sensitivity analysis
- 比较 no-cap、24h cap、6h cap 下的结果

结果显示：
- no cap：`447` markets，Brier `0.0615`
- within 24h：`428` markets，Brier `0.0627`
- within 6h：`410` markets，Brier `0.0640`

也就是说，核心结果方向非常稳定，不是被少数 stale candles 撑出来的。

#### 困难 5：不同 horizon 的 matched sample 不一样

这不是 bug，而是现实数据的一部分：
- 1d matched = `166`
- 6h matched = `279`
- 1h matched = `295`
- last pre-close matched = `447`

原因是不同市场的 candle 可用性不同。这个事实如果不提前讲，面试官会自然追问：
“你是不是拿同一批市场比较了四个时点？”

所以我在 README 和分析里明确写了：
matched sample varies by horizon because candle availability differs across markets.

### 9. 结果到底说明了什么？

最重要的主线有两条：

#### 主线 A：Accuracy improves near close

Brier score 从：
- `0.1854` at `1d_before_close`
- 到 `0.0615` at `last_preclose`

说明市场在接近结算时，概率预测整体更接近最终结果。

#### 主线 B：Price paths separate by eventual outcome

eventual Yes / No 的平均概率路径从：
- `0.56 vs 0.31` at `1d_before_close`
- 变成 `0.88 vs 0.13` at `last_preclose`

说明随着 close 接近，市场价格对最终结果的区分能力明显增强。

### 10. 这个项目最能体现什么能力？

这个项目比第一个项目更能体现五种能力：

- 研究设计：先定义 universe、窗口、抽样和时间点
- 工程控制：避免全量 candles，改成先抽样再定向抓取
- event-time 数据处理：把不同市场放到统一的“距 close 还有多久”的坐标上
- 概率预测评估：用 Brier、MAE、calibration 和 path separation，而不是只看准确率
- 数据诊断与修正：发现 count 定义问题、edge-case 时间戳问题和 stale-candle 问题后能主动修正

## 五、高频面试问答速记

### Q1. 为什么第二个项目比第一个项目更像 quant research？

因为它不再只是静态地问“这个概率准不准”，而是在问“信息是怎么随着时间进入价格的”。这更像 market microstructure / forecasting 研究。

### Q2. 为什么不抓全量 candles？

因为那样工程规模会失控，而且研究设计会变差。更好的做法是先定义 universe，再抽样，再只对样本抓取 candles。

### Q3. 为什么选 600 个市场？

因为这个数量已经足够支持 event-time metrics 和核心图表，同时还保持工程可复现、结果可解释。

### Q4. 为什么 matched sample 在不同 horizon 不一样？

因为不同市场的 candlestick 可用性不一样。不是每个市场都能在 `1d / 6h / 1h` 三个窗口里找到满足容忍范围的 candle。

### Q5. 如果有人质疑 last-preclose 可能离 close 太远怎么办？

我已经专门做了 gap sensitivity analysis。把 last-preclose 收紧到 `24h` 和 `6h` 之后，Brier score 和 Yes/No separation 方向基本不变，所以主结果不是被少数 stale candles 人为撑出来的。

### Q6. 这个项目里最难的地方是什么？

最难的不是画图，而是保证样本构造和时间对齐是真正可信的。包括：
- unique market counts 的定义
- fixed-window universe 的口径
- stale candles 的处理
- 不同 horizon matched sample 的解释

### Q7. 如果继续升级，你会做什么？

- 用不同随机种子重复分层抽样
- 按 market category 比较路径和误差
- 改成多个 candle resolution 做对比
- 比较更严格的 near-close cap 规则

## 六、最值得背下来的 20 秒总结

这个项目研究的是预测市场价格在接近结算时是否会变得更准确、并且更清楚地区分最终结果。我先用 metadata 定义 universe，再按月份和流动性做 600 个市场的分层抽样，只对样本 ticker 下载 candlesticks，并提取固定 event-time 时点的隐含概率。结果显示 Brier score 随着接近 close 明显下降，eventual Yes 和 eventual No 的价格路径也明显拉开；同时我还专门检查了 unique sample counts 和 stale-candle sensitivity，确保这个结果不是数据构造造成的假象。
