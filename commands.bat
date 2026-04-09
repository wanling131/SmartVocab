@echo off
REM SmartVocab 常用命令快捷方式
REM 使用: commands.bat <command>

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="run" goto run
if "%1"=="test" goto test
if "%1"=="test-unit" goto test-unit
if "%1"=="test-e2e" goto test-e2e
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="clean" goto clean
if "%1"=="install" goto install
if "%1"=="db-test" goto db-test
goto unknown

:help
echo.
echo SmartVocab 常用命令:
echo.
echo   commands.bat run         启动开发服务器
echo   commands.bat test        运行所有单元测试
echo   commands.bat test-unit   运行单元测试（快速模式）
echo   commands.bat test-e2e    运行 E2E 测试
echo   commands.bat lint        代码检查 (flake8 + isort)
echo   commands.bat format      格式化代码 (black + isort)
echo   commands.bat clean       清理缓存和临时文件
echo   commands.bat install     安装依赖
echo   commands.bat db-test     测试数据库连接
echo.
goto end

:run
python main.py
goto end

:test
python -m pytest tests/ -v --tb=short
goto end

:test-unit
set SMARTVOCAB_SKIP_DL_INIT=1
python -m pytest tests/ -v --tb=short
goto end

:test-e2e
cd tests\e2e
npx playwright test
goto end

:lint
flake8 api/ core/ tools/ --max-line-length=100 --extend-ignore=E203,W503
isort --check-only --profile=black api/ core/ tools/
goto end

:format
black --line-length=100 api/ core/ tools/
isort --profile=black api/ core/ tools/
goto end

:clean
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rd /s /q "%%d"
if exist .coverage del .coverage
if exist htmlcov rd /s /q htmlcov
echo 缓存已清理
goto end

:install
pip install -r requirements.txt
cd tests\e2e
npm install
goto end

:db-test
python -c "from tools.database import test_connection; test_connection()"
goto end

:unknown
echo 未知命令: %1
echo 使用 commands.bat help 查看可用命令
goto end

:end