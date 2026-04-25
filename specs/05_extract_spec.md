# 文献初步扫描规范 (Initial Paper Scanning Specification)

## 1. 目标
对指定项目关联的 Zotero Collection 中的所有论文进行快速结构化扫描，利用 LLM 提取核心信息，生成便于横向对比的 CSV 文献综述表。

## 2. 输入要求
- **项目名称 (Project Name)**: 对应 Zotero 中的 Collection 名称。
- **文献源**: Zotero 指定 Collection 下的所有条目及其 PDF 附件。
- **提取方法**: 八要素法。

## 3. 提取字段定义 (八要素法)
对于每一篇论文，需提取以下信息：
1. **作者 (Author)**: 仅保留前三位作者，其余用 et al. 表示。
2. **单位 (Institution)**: 第一作者所属的主要研究机构。
3. **时间 (Date)**: 论文发表年份。
4. **题目 (Title)**: 论文完整标题。
5. **研究目的 (Research Objective)**: 核心解决的问题或研究动机（建议 1-2 句）。
6. **方法 (Methodology)**: 采用的关键算法、实验设计或技术路线。
7. **结果 (Results)**: 主要实验数据、结论或性能提升。
8. **即时感想 (Reflections)**: 预留列，默认留空，或由 LLM 根据论文创新性给出一句评价。

## 4. 处理逻辑
1. **获取列表**: 调用 Zotero API 获取指定 Collection 的所有 Item Key。
2. **全文读取**: 
   - 遍历条目，优先寻找 PDF 附件。
   - 使用 `read_pdf_content` 提取前 10-15 页内容（通常涵盖八要素所需信息）。
3. **LLM 处理**: 
   - 将文本送入 LLM，按照 Prompt 模板进行八要素提取。
4. **数据汇总**:
   - 将提取的结果合并。
   - 转换为 CSV 格式。

## 5. 输出规范
- **文件路径**: `projects/{project_name}/05_summary.csv`
- **格式**: UTF-8 编码，包含表头：`Author,Institution,Date,Title,Objective,Methodology,Results,Reflections`

## 6. Prompt 模板示例
```text
请作为一名资深学术研究员，阅读以下论文片段，并严格按照“八要素法”提取信息。
要求：
- 语言简洁，学术严谨。
- 若无法找到某项信息，请填写 "N/A"。
- 输出格式必须为：作者 | 单位 | 时间 | 题目 | 研究目的 | 方法 | 结果 | 即时感想
```
