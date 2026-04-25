# Zotero PDF 同步规范 (Zotero PDF Sync Specification)

## 1. 目标
自动将本地项目目录中的 PDF 论文同步到 Zotero 指定的 Collection 中，确保文献库与本地科研进度同步。

## 2. 输入要求
- **项目名称 (Project Name)**: 脚本运行时需指定项目名称（如 `symbol_recognition`）。
- **本地路径**: `projects/{project_name}/03_pdfs/`。该目录下存放待同步的 PDF 文件。
- **环境变量**: 需从 `.env` 加载 `ZOTERO_USER_ID` 和 `ZOTERO_API_KEY`。

## 3. Zotero 结构规范
- **Collection 名称**: 必须与 `{项目名称}` 完全一致。
- **层级结构**: 默认在 Zotero 根目录下查找或创建该 Collection。

## 4. 同步逻辑与边界
1. **环境检查**: 验证 `.env` 配置及本地 `03_pdfs` 目录是否存在。
2. **Collection 处理**:
   - 检查 Zotero 中是否存在同名 Collection。
   - **不存在**: 新建该 Collection。
   - **已存在**: 获取其 `collection_key`。
3. **文件同步 (Incremental Sync)**:
   - 遍历本地 `03_pdfs` 文件夹下的所有 `.pdf` 文件。
   - **重复检查**: 检查该 Collection 下是否已存在同名附件（Attachment）或同名条目。
   - **上传逻辑**:
     - 若不存在，则作为新条目上传 PDF，并触发 Zotero 的元数据抓取（如果可能）或简单作为附件条目。
     - 若已存在，则跳过，避免重复上传。
4. **清理与日志**: 记录同步成功、跳过及失败的文件。

## 5. 异常处理
- 网络连接超时需有重试机制或清晰报错。
- API 权限不足需提示检查 `API_KEY` 权限（需开启 Allow library access）。
- PDF 文件损坏或无法读取时需跳过并记录。
