"""知识库命令入口 —— 改 ARGS 就能执行任意 chatchat kb 子命令

注意：0.3.1.3 的 CLI 只做「向量库维护」，新建知识库 / 上传文件请用 WebUI 或 HTTP API。

可用参数（chatchat kb --help）：
    -r, --recreate-vs   重建向量库（换 embedding 模型后必须执行）
    -i, --increment     增量：把本地新文件入库
    -u, --update-in-db  只重建数据库中已登记文件的向量
    -n, --kb-name       指定知识库名，默认处理全部
    -e, --embed-model   指定 embedding 模型
    --create-tables     建空表
    --clear-tables      清空表（危险）
    --prune-db / --prune-folder  清理数据库与本地目录的不一致项

示例：
    ["kb", "-r"]                        重建全部知识库
    ["kb", "-r", "-n", "samples"]       只重建 samples
    ["kb", "-i", "-n", "samples"]       增量入库
"""

import sys

from _env import ensure_env

ensure_env()  # 环境变量 / 工作目录 / 解释器自检，必须在 import chatchat 之前

from chatchat.cli import main

ARGS = ["kb", "-r", "-n", "samples"]

if __name__ == "__main__":
    sys.argv = ["chatchat"] + ARGS
    main()
