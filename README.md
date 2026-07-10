<div align="center">

**中文** · [English](README.en.md)

# Repo Learning

### 输入一个仓库，得到一座项目学习网站。

把陌生代码库变成一份可离线阅读、循序学习的项目介绍。

</div>

## 它会讲清楚什么

- 项目解决什么问题
- 核心模块如何连接
- 一次请求、任务或事件如何流转
- 哪些领域概念最重要
- 哪些文件最值得先读
- 新贡献者应该按什么顺序学习

输出不是固定格式的审计报告。网站会根据仓库内容动态选择章节，并生成架构图、流程故事、概念卡片、代码地图和学习路线。

## 使用

在支持 Skill 的 Agent 中：

```text
使用 $repo-learning 学习 https://github.com/owner/repository，生成并打开学习网站。
```

就这一句。用户不需要克隆仓库、准备 JSON、选择图表或运行生成器。Skill 会自动完成仓库解析、源码调查、证据建模、内容质检、网页生成和浏览器阅读验收，最后返回可直接打开的 `index.html`。

内部流水线由以下确定性工具提供护栏：

```bash
# 1. 准备远程或本地仓库
python3 scripts/prepare_repo.py https://github.com/owner/repository \
  --json-out /tmp/repo-source.json

# 2. 为 Agent 生成安全、有限的仓库清单
python3 scripts/inventory_repo.py /tmp/resolved-repo \
  --json-out /tmp/inventory.json

# 3. Agent 深入调查源码并生成 /tmp/site_data.json

# 4. 拒绝只有 README 摘要、缺少真实架构与流程的空壳内容
python3 scripts/quality_check.py /tmp/site_data.json \
  --repo /tmp/resolved-repo \
  --strict

# 5. 生成网站
python3 scripts/generate_report.py \
  --input /tmp/site_data.json \
  --out /tmp/repo-learning-site \
  --strict

# 6. 校验并在浏览器中检查语义内容
python3 scripts/validate_report.py /tmp/repo-learning-site --strict
open /tmp/repo-learning-site/index.html
```

## 网站能力

- 源码证据架构关系图
- 关键运行流程
- 领域概念与代码入口
- Contributor 学习路径
- 行内源码证据与命令文本
- 无 CSS、无内联样式、无展示用运行时脚本
- 单文件 HTML，无远程可执行资源
- 兼容旧版 `report_data.json` v1

## 安装

```bash
git clone https://github.com/tt-a1i/repo-learning.git
cd repo-learning
./install.sh
```

开发模式可以使用软链接：

```bash
./install.sh --link
```

## 自检

```bash
bash scripts/self_check.sh
```

回归集覆盖仓库清单、内容质量门、v2 网站生成、旧版数据兼容、架构与流程组件、远程资源拦截、XSS 转义、坏数据拒绝和 Repo 输入解析。

## License

MIT
