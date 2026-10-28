# Langchain-Chatchat 二次开发工程

> 这是一个**可运行、可改、可讲**的工程：源码可编辑（`src/`），有架构文档、面试题库、
> 改进路线图，以及离线可跑的冒烟测试。

## 文档索引

| 文档 | 内容 |
|---|---|
| [`docs/01-架构与源码导读.md`](docs/01-架构与源码导读.md) | 分层架构、RAG 全链路 15 步（带行号）、类图、10 个代码问题、3 天阅读计划 |
| [`docs/02-面试题库.md`](docs/02-面试题库.md) | 41 道面试题 + 答题骨架，含性能优化、故障排查、设计追问 |
| [`docs/03-改进路线图.md`](docs/03-改进路线图.md) | 已完成的改动、现状诊断、P0~P3 优先级、每项改动的代码方案与验证方法 |

## 模型接入：DeepSeek（已接通）+ 本地 Ollama

两条链路同时可用，**职责分开**：

| 用途 | 模型 | 走哪 | 为什么 |
|---|---|---|---|
| 对话生成（LLM） | `deepseek-chat`（默认） | DeepSeek 云端 | 3B 本地模型答得太浅，写进简历的 RAG 效果需要更好的生成质量 |
| 向量化（Embedding） | `bge-m3` | 本地 Ollama | DeepSeek 没有 embedding 接口，而且向量化调用量大，本地免费且快 |

### 密钥怎么放

密钥只写在 `.env`（已 gitignore，`git ls-files` 里没有它）：

```
DEEPSEEK_API_KEY=sk-...
```

配置文件 `D:\chatchat-data\model_settings.yaml` 里只出现占位符：

```yaml
  - platform_name: deepseek
    platform_type: deepseek
    api_base_url: https://api.deepseek.com/v1
    api_key: ${DEEPSEEK_API_KEY}
```

`${...}` 由 `settings.py` 的 `PlatformConfig.expand_env_vars`（field_validator）在
加载配置时展开。这样 yaml 可以放心提交进 git，仓库里永远没有明文密钥。

> `.env` 的优先级**高于**系统环境变量（`_env.py:_load_dotenv` 是覆盖写入）。
> 之前系统里留着一个过期的 `DEEPSEEK_API_KEY`，导致改 `.env` 完全不生效，
> 所以特意改成覆盖语义。

### 命令

```bash
python tools\enable_deepseek.py                    # 沿用 .env 里的 key，注册平台
python tools\enable_deepseek.py --set-default      # 同时设为默认 LLM（当前状态）
python tools\enable_deepseek.py --api-key sk-xxx   # 换 key 并重新注册
python tools\enable_deepseek.py --remove           # 移除平台，默认模型回到 qwen2.5:3b
```

### 当前账号实际可用的模型

`GET https://api.deepseek.com/v1/models` 返回的是 `deepseek-flash`、`deepseek-v4-pro`；
`deepseek-chat` 是官方稳定别名，网关会把它路由到 `deepseek-flash`（响应里的
`model` 字段能看到重定向）。配置里两种名字都列了，避免下拉框里选不到。

实测一条命令验证：

```bash
curl -s --noproxy "*" -X POST http://127.0.0.1:7861/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"deepseek-chat\",\"messages\":[{\"role\":\"user\",\"content\":\"你好\"}]}"
```

## 目录结构

```
D:\chatchat-project\
├── src\chatchat\            ← 真正被加载的源码（改这里即时生效）
├── docs\                    架构 / 面试 / 路线图
├── tools\
│   ├── enable_deepseek.py      一键接入 DeepSeek（可重复执行，自带自检）
│   └── mock_llm_server.py      离线 OpenAI 兼容桩，没 Key 也能开发测试
├── tests\
│   └── test_rag_pipeline.py    RAG 全链路冒烟测试
├── _env.py                  环境自检：配置 / 解释器切换 / 源码优先加载
├── run_all.py  run_api.py  run_webui.py  run_kb.py
├── stop_all.py  →  停止-Chatchat.bat
└── .env                     密钥（已 gitignore）
```

## 开发模式说明

`_env.py` 会把 `src\` 插到 `sys.path` 最前面，所以 `import chatchat` 加载的是
`src\chatchat\`，**改完代码重启进程即生效**，不用重新 `pip install`。

想对照原始安装包（`site-packages`）的行为：

```bash
set CHATCHAT_USE_SRC=0 && python run_api.py
```

---

# 附：PyCharm 运行环境配置

## 一、配置解释器（只需一次）

1. `File` → `Open`，选这个目录：`D:\chatchat-project`
2. `File` → `Settings` → `Project: chatchat-project` → `Python Interpreter`
3. 点齿轮 → `Add Interpreter` → `Add Local Interpreter`
4. 左侧选 `Conda`，`Conda executable` 选 `D:\miniconda\Scripts\conda.exe`，
   然后 `Use existing environment` 下拉里选 **`chatchat`**
   （或直接选 `System Interpreter` → `D:\miniconda\envs\chatchat\python.exe`）
5. OK。底部状态栏应显示 `Python 3.11 (chatchat)`

### 如果打开项目后报 `ModuleNotFoundError: chatchat`

先看项目里有没有 `.venv` 目录。PyCharm 2026 版打开项目时可能会自作主张建一个
虚拟环境，本机上它建出来的是：

```
D:\chatchat-project\.venv\pyvenv.cfg
    home = D:\python
    version = 3.14.7
```

这是 **Python 3.14 的空环境**，和 ChatChat 完全无关。同时 `.idea\chatchat-project.iml`
里登记的 SDK 是 `D:\miniconda\envs\chatchat-project` —— 这个环境**根本不存在**。

处理办法（按第 1～5 步改完解释器后）：

- `.venv` 可以整个删掉，它没有任何用处。
- 另有一个 **PyCharm 自动创建的 conda 环境** `D:\miniconda\envs\chatchat-project`
  （Python **3.13**.18，167MB，里面没装 chatchat），chatchat 只支持 3.8–3.11，
  这个环境永远用不上。删掉：
  ```
  D:\miniconda\Scripts\conda.exe env remove -n chatchat-project -y
  ```
- `Settings` → `Python Interpreter` → 齿轮 → `Show All`，把
  `D:\miniconda\envs\chatchat-project` 和 `D:\chatchat-project\.venv` 两条无效记录删掉。
- 只保留 `D:\miniconda\envs\chatchat`。

## 二、启动

打开对应文件，右上角绿色三角 → `Run 'xxx'`（调试用虫子图标 `Debug`）。
| 文件 | 作用 | 端口 |
|---|---|---|
| `run_all.py` | 一键启动 API + WebUI（自己用 subprocess 拉起下面两个脚本） | 7861 / 8501 |
| `run_api.py` | 只启动 API（单进程，**可打断点**） | 7861 |
| `run_webui.py` | 只启动 WebUI（单进程，**可打断点**） | 8501 |
| `run_kb.py` | 知识库维护命令，改文件里的 `ARGS` | — |
| `stop_all.py` | 停止服务，释放 7861 / 8501 | — |

`stop_all.py` 也可以直接双击 `停止-Chatchat.bat`。遇到任何「端口被占用」的问题，
先跑它再重新启动。

调试顺序：先 `run_api.py`，再 `run_webui.py`，两个窗口同时跑。

所有脚本内部已经设好 `CHATCHAT_ROOT=D:\chatchat-data` 并切到该目录，
**不需要**在 PyCharm 里额外配环境变量或工作目录。

### 解释器选错也能跑

四个脚本第一步都调用 `_env.py` 的 `ensure_env()`。它会检查当前解释器里能否
`import chatchat`，如果不能（比如 PyCharm 用的是 `D:\python`），就自动用
`D:\miniconda\envs\chatchat\python.exe` 重新拉起本脚本，并打印：

```
====================================================================
[环境自检] 当前解释器里没有 chatchat，正在自动切换。
  当前解释器：D:\python\python.exe
  切换为    ：D:\miniconda\envs\chatchat\python.exe
====================================================================
```

所以即使第 1 步没配好，`Run` 也能正常起来。**但 `Debug` 不行**——调试器挂在
旧进程上，切换后断点不会命中。要断点调试必须按第 1 步把解释器设对。

搬动数据目录时改 `_env.py` 顶部的 `CHATCHAT_ROOT` / `CONDA_PYTHON` 两个常量即可。

## 三、为什么 run_all.py 打断点不生效

因为它自己就是进程管理器：用 `subprocess` 分别拉起 `run_api.py` 和 `run_webui.py`，
每个都是一个独立进程。PyCharm 的调试器只挂在 `run_all.py` 那个进程上，
两个子进程里的断点不会命中。

要调业务代码，就开两个运行窗口分别跑 `run_api.py` 和 `run_webui.py`（先 API 后 WebUI），
单进程内直接执行，断点正常命中。

### 为什么不用官方 `chatchat start -a`

`startup.py` 用 `multiprocessing(spawn)` 起子进程，spawn 出来的进程**不继承**
父进程往 `sys.path` 里插的 `src\` 目录，也不走 `_env.py` 的环境自检。
实测结果：API 起来了，WebUI 的 8501 始终不监听，连 `logs\run_webui_*` 目录都不生成，
全程一句报错都没有。

改成 subprocess 之后：日志互不污染、一个挂了另一个还能看日志、Ctrl+C 一次带走两个，
冷启动 20 秒双端口就绪（旧方式 40 秒以上，还时好时坏）。

## 四、源码在哪里、怎么改

**运行时加载的是 `D:\chatchat-project\src\chatchat\`**（`_env.py` 把它插到 `sys.path`
最前面）。在 PyCharm 里 `Ctrl+Shift+N` 搜类名跳进去，下断点能命中，改完重启即生效，
不需要重新 `pip install`。

`site-packages` 里那份是 `pip install` 装的原始包，现在只作为对照存在，
设 `CHATCHAT_USE_SRC=0` 可以切回去对比行为。

如果想改成「git 管理的 editable 安装」也可以，但**只能用 v0.3.1.3 的 tag**：

**⚠️ 不要把 GitHub master 分支的源码装进这个环境。**
master 比 0.3.1.3 多了 MCP 功能，依赖里有 `mcp>=1.4.1`，而 `mcp` 要求 `pydantic>=2.8`，
会把环境的 pydantic 从 2.7.4 顶到 2.14，导致 FastAPI 0.109 栈直接崩：
`ImportError: cannot import name 'eval_type_backport'`。
只有 **v0.3.1.3 的 tag 源码**依赖和 PyPI 包完全一致，可以安全 editable 安装。

v0.3.1.3 tag 源码的安装方式（已验证构建链路可用）：

```bash
git clone --branch v0.3.1.3 --depth 1 https://github.com/chatchat-space/Langchain-Chatchat.git D:\Langchain-Chatchat
D:\miniconda\envs\chatchat\Scripts\uv.exe pip install -e D:\Langchain-Chatchat\libs\chatchat-server ^
    --no-deps --no-build-isolation ^
    --python D:\miniconda\envs\chatchat\python.exe
```

要点：必须 `--no-deps`（依赖已装好，让它重新解析会把版本搞乱）、
`--no-build-isolation`（poetry-core 已装进环境，避免隔离构建时被安全策略拦）。

装完 `python -c "import chatchat; print(chatchat.__file__)"` 应指向源码目录。

回滚成官方包：

```bash
D:\miniconda\envs\chatchat\Scripts\uv.exe pip install --reinstall --no-deps ^
    D:\chatchat-tmp\langchain_chatchat-0.3.1.3-py3-none-any.whl ^
    --python D:\miniconda\envs\chatchat\python.exe
```

## 五、绝对不要运行的文件

| 文件 | 为什么不能跑 |
|---|---|
| `release.py` | 发版脚本：调 `git tag` 算版本号、改 pyproject 的 version。ZIP 下载的目录没有 `.git`，必然报 `fatal: not a git repository` 和 `CalledProcessError: ['git','tag']` |
| `docker/` 下脚本 | 走容器，和本机环境无关 |

启动入口只有 `run_all.py` / `run_api.py` / `run_webui.py`。

## 六、常见问题


- **报 `ModuleNotFoundError: chatchat`**：解释器选错了。现在的脚本会自动切换，
  看到 `[环境自检] ... 正在自动切换` 就说明在纠正这个错误，属正常现象。
  想彻底消除：按第 1 步把解释器设成 `chatchat`，状态栏应显示 `Python 3.11 (chatchat)`，
  不能是 `Python 3.13 (D:\python)`。
  若已显示 `Python 3.11 (chatchat)` 仍报这个错，说明包被卸了，重装：
  ```
  D:\miniconda\envs\chatchat\Scripts\uv.exe pip install --reinstall --no-deps ^
      D:\chatchat-tmp\langchain_chatchat-0.3.1.3-py3-none-any.whl ^
      --python D:\miniconda\envs\chatchat\python.exe
  ```
- **报 `[Errno 10048] ... bind on address ('127.0.0.1', 7861)`**
  或 **`Port 8501 is already in use`**：端口被占了，之前启动的实例没退干净。
  现在脚本会先自检并直接告诉你占用 PID，照提示处理即可；最省事的是双击
  `停止-Chatchat.bat`（内部就是 `stop_all.py`）。

- **WebUI 打开了但下拉框是空的**：API 没起来。`run_webui.py` 会在启动时提示
  `API（7861）没有在运行`，另开一个窗口跑 `run_api.py`。
- **报 `PermissionError: chatchat.log`**：上一个进程没退干净，任务管理器结束残留的
  `python.exe` 后重试。
- **WebUI 一直转圈 RUNNING**：API 没起来，先看 7861 端口是否在监听。
- **终端里 Ctrl+C 停不掉**：在 PyCharm 的运行窗口点红色方块 `Stop`。
- **`fatal: not a git repository`**：你在跑 `release.py`，见第五节。
