# automation

毕业设计用**自动化自检脚本**，与主业务无关；不需要时**删除本文件夹**即可。

## 运行（在项目根目录）

- `python automation/smoke_check.py --quick` — 仅首页 + `/api/health`（最快）
- `python automation/smoke_check.py` — 含**智能推荐模块**调用 + 全量 HTTP GET
- `python automation/smoke_check.py --recommend-only` — 只测推荐引擎（需 MySQL，可不装 Flask）
- `python automation/smoke_check.py --skip-recommend` — 只做 HTTP，不跑推荐引擎

脚本会默认设置 `SMARTVOCAB_SKIP_DL_INIT=1`，避免导入时触发深度学习自动训练；若需完整加载模型：`set SMARTVOCAB_SKIP_DL_INIT=0` 后再运行。

依赖：`pip install -r requirements.txt`（其中已固定 `werkzeug<3` 以兼容 Flask 2.3 的 `test_client`）。
