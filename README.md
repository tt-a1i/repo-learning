<div align="center">

**中文** · [English](README.en.md)

# Repo Learning

### 输入一个仓库，得到一份精致的项目学习页。

</div>

## 它做什么

给 Agent 一个仓库地址，它会：

1. 克隆到临时目录（只读调查）
2. 讲清项目价值、架构与脉络原理（不抠实现细节）
3. 按内置 HTML 模板生成**一页**好看的学习站
4. 用 Mermaid 架构图 / 主流程把因果讲清楚

你得到的是可直接打开的 `index.html`，不是中间 JSON，也不是校验报告。

## 使用

在支持 Skill 的 Agent 里：

```text
用 repo-learning 学习 https://github.com/owner/repository
```

## 安装

```bash
git clone https://github.com/tt-a1i/repo-learning.git
cd repo-learning
./install.sh
```

开发可用软链接：

```bash
./install.sh --link
```

## 结构

```text
SKILL.md                            # Agent 主流程
assets/learning-page.template.html  # 精致单页模板
references/analysis-guide.md        # 调查与图表指引
PRODUCT.md                          # 产品原则
install.sh                          # 安装到各 Agent skills 目录
```

## License

MIT
