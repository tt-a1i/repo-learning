<div align="center">

**中文** · [English](README.en.md)

# Repo Learning

### 输入一个仓库，得到一座项目学习网站。

把陌生代码库变成一份可以浏览、探索和循序学习的项目介绍。

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

完整流程：

```bash
# 1. 准备远程或本地仓库
python3 scripts/prepare_repo.py https://github.com/owner/repository \
  --json-out /tmp/repo-source.json

# 2. Agent 调查仓库并生成 /tmp/site_data.json

# 3. 生成网站
python3 scripts/generate_report.py \
  --input /tmp/site_data.json \
  --out /tmp/repo-learning-site \
  --strict

# 4. 校验并打开
python3 scripts/validate_report.py /tmp/repo-learning-site --strict
open /tmp/repo-learning-site/index.html
```

## 网站能力

- 交互式架构关系图
- 关键运行流程
- 领域概念与代码入口
- Contributor 学习路径
- 源码位置一键复制
- 响应式布局、深浅主题、打印和 reduced-motion
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

回归集覆盖 v2 网站生成、旧版数据兼容、架构与流程组件、远程资源拦截、XSS 转义、坏数据拒绝和 Repo 输入解析。

## License

MIT
