# 创业板指 (399006) 量化交易机器人

这是一个基于 Python 的量化交易系统，专门用于监控和交易创业板指 (399006)。它包含从数据获取、信号计算、策略回测到自动化通知的全流程功能。

## 核心功能

1.  **数据层 (Data Layer)**: 使用 `AkShare` 获取创业板指的历史行情、估值数据 (PE-TTM/PB)、宏观数据 (十年期国债收益率) 和北向资金流向。数据存储在 SQLite 数据库中。
2.  **信号层 (Signal Layer)**: 计算 PE 分位 (5年/10年)、20日均线乖离率、成交量比率 (量能萎缩信号) 等核心指标。
3.  **策略层 (Strategy Layer)**:
    *   **核心引擎**: 策略逻辑由 `decision_engine.py` 统一管理，确保回测、实盘和看板逻辑一致。
    *   **买入条件**:
        *   **估值**: PE分位 < 40% (原30%，已优化)。
        *   **情绪**: 量能萎缩 (5日均量 < 60日均量的 1.2倍)。
        *   **宏观滤网 (新增)**: 十年期国债收益率需处于下行趋势 (Liquidity Check)。
    *   **网格加仓**: 持仓亏损 5% 时加仓一档 (最多 3 档，总仓位上限 30%)。
    *   **卖出**: 估值过热 (PE分位 > 70%) 或 情绪狂热 (乖离率 > 15%)。
4.  **回测 (Backtest)**: 基于 `Backtrader` 框架的历史回测 (2018年至今)。
5.  **自动化 (Automation)**: 每日定时任务 (15:30)，自动更新数据、判断信号并通过 PushPlus/邮件 发送通知。
*   **可视化 (Dashboard)**: 基于 Streamlit 的交互式 Web 仪表盘。
    *   **实时调参**: 支持在侧边栏动态调整策略参数 (PE/Vol 阈值、是否启用宏观滤网等) 并实时保存配置。

## 安装说明

确保安装 Python 3.8+。

```bash
# 克隆仓库
git clone <repository_url>
cd <repository_folder>

# 安装依赖
pip install -r requirements.txt
```

## 使用指南

### 1. 初始化数据

首次运行时，系统会自动创建 `stock_data.db` 数据库并下载历史数据。你可以直接运行数据加载脚本来测试数据获取：

```bash
python data_loader.py
```

### 2. 运行回测

查看策略在历史数据上的表现 (2018-至今)：

```bash
python run_backtest.py
```

输出将包含：
*   最终资金权益
*   夏普比率 (Sharpe Ratio)
*   最大回撤 (Max Drawdown)
*   胜率和盈亏比
*   策略收益 vs 基准收益 (买入持有)

### 3. 开启自动化监控

运行主程序，开启每日定时任务 (默认 15:30 运行)。主程序会加载 `strategy_config.json` 中的配置：

```bash
python main.py
```

如果想立即运行一次以测试信号通知：

```bash
python main.py --once
```

### 4. 启动可视化看板

启动 Web 仪表盘，查看实时行情、策略信号和网格交易位置：

```bash
streamlit run dashboard.py
```

浏览器会自动打开 (默认 `http://localhost:8501`)。在看板中调整的参数会自动保存，并立即生效于自动化监控任务。

### 5. 配置通知

在 `notifier.py` 文件中配置你的推送服务 Token (推荐使用 PushPlus)：

```python
def notify(title, message):
    # 将此处替换为你的 PushPlus Token
    TOKEN = "YOUR_PUSHPLUS_TOKEN"
    ...
```

目前代码中 `send_pushplus` 函数处于模拟模式 (Mock)，只会打印日志。如需真实发送，请取消注释 `requests.post` 相关代码。

## 文件结构

*   `main.py`: 自动化主程序 (入口)。
*   `dashboard.py`: 可视化看板 (Streamlit)。
*   `decision_engine.py`: **[新增]** 核心交易决策引擎。
*   `config.py`: **[新增]** 策略配置管理。
*   `strategy.py`: Backtrader 策略类定义。
*   `run_backtest.py`: 回测脚本。
*   `data_loader.py`: 数据获取与存储 (ETL)。
*   `signal_calculator.py`: 核心指标计算。
*   `optimize_strategy.py`: **[新增]** 策略参数自动优化脚本。
*   `notifier.py`: 通知模块 (PushPlus/Email)。

## 注意事项

*   **数据源**: 本项目依赖 `AkShare` 接口。若接口变动或失效，需更新 `data_loader.py` 中的相关函数。
*   **实盘风险**: 本项目仅供学习和研究使用，不构成投资建议。量化策略在实盘中可能面临滑点、交易成本和模型失效等风险。
