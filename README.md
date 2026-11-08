# MiniVMS智能视频设备管理与告警平台测试项目

面向软件产品测试岗位设计的个人项目，模拟小型视频设备管理平台，完整实践需求分析、接口开发、测试用例设计、自动化测试、缺陷闭环、回归测试和测试报告输出。

## 项目成果

- 梳理登录、设备管理、状态监控、角色权限和告警处理需求。
- 使用FastAPI开发可测试的REST API。
- 使用SQLite实现设备与告警数据持久化。
- 使用pytest完成68项自动化测试，全部通过。
- 覆盖正常、异常、边界值、权限和状态流转场景。
- 发现并修复设备端口字段缺失问题，完成缺陷记录和回归验证。
- 使用pytest-html生成可独立打开的HTML测试报告。
- 使用Git保存功能开发、缺陷修复和测试迭代记录。
- 在 WSL2 Ubuntu 环境部署 MiniVMS，验证服务重启后的数据持久化；完成 SQLite 手动备份与独立副本恢复，通过完整性检查、设备及告警数据核对、恢复后写入和原系统对照验证，整理部署、操作及维护说明。

## 功能范围

### 用户登录

- 管理员、操作员和访客三种角色。
- 验证正确登录、错误密码、用户不存在和空字段等场景。

### 设备管理

- 新增、查询、修改和删除设备。
- 校验IPv4/IPv6地址和端口范围。
- 使用IP地址与端口组合判断重复设备。
- 支持在线、离线和故障状态更新与筛选。
- 仅管理员可以修改和删除设备。
- 使用SQLite保存设备信息，服务重启后数据仍然存在。

### 告警管理

- 创建、查询和筛选告警。
- 告警状态按照以下顺序流转：

  新产生 → 已确认 → 处理中 → 已关闭

- 管理员和操作员可以处理告警。
- 访客只能查看告警。
- 拒绝非法状态跳转。
- 关闭告警前必须填写有效的处理说明。

## 技术栈

- Python 3.14
- FastAPI
- Pydantic
- SQLite
- pytest
- FastAPI TestClient
- pytest-html
- Git

## 自动化测试

项目当前包含68项自动化测试：

| 测试模块 | 测试数量 | 主要覆盖内容 |
|---|---:|---|
| 登录模块 | 9 | 正常登录、异常登录、输入校验 |
| 设备模块 | 37 | 增删改查、边界值、状态、权限、重复校验 |
| 告警模块 | 22 | 创建查询、筛选、状态流转、权限和异常处理 |
| 合计 | 68 | 功能、异常、边界、权限和回归测试 |

完整HTML测试报告：

`reports/full-test-report.html`

## 项目结构

```text
MiniVMS-Test/
├── app/
│   ├── database.py
│   └── main.py
├── docs/
│   ├── 01-需求说明书.md
│   ├── 02-登录模块测试用例.md
│   ├── 03-缺陷报告-BUG-DEVICE-001.md
│   ├── 04-告警模块测试用例.md
│   ├── 05-部署说明.md
│   ├── 06-用户操作与权限说明.md
│   ├── 07-备份恢复演练记录.md
│   └── 08-日常检查与故障处理.md
├── evidence/
│   ├── 01-告警关闭.png
│   ├── 02-服务重启.png
│   ├── 03-数据库备份.png
│   ├── 04-恢复完整性检查.png
│   ├── 05-恢复后的告警.png
│   ├── 06-恢复后的写入.png
│   ├── 07-恢复副本设备数3.png
│   └── 08-原系统设备数2.png
├── reports/
│   ├── login-test-report.html
│   └── full-test-report.html
├── tests/
│   ├── test_login.py
│   ├── test_devices.py
│   └── test_alarms.py
├── .gitignore
├── README.md
└── requirements.txt
```

## 本地运行

创建并启用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
python -m pip install -r requirements.txt
```

启动服务：

```bash
python -m uvicorn app.main:app --reload
```

打开Swagger接口文档：

`http://127.0.0.1:8000/docs`

## 运行自动化测试

```bash
python -m pytest -v
```

生成HTML报告：

```bash
python -m pytest -v \
  --html=reports/full-test-report.html \
  --self-contained-html
```

打开报告：

```bash
open reports/full-test-report.html
```

## 权限请求头

调用受权限控制的接口时，需要填写：

```text
X-User-Role: admin
```

支持的角色值：

- `admin`：管理员
- `operator`：操作员
- `visitor`：访客

## 缺陷闭环示例

项目测试过程中发现设备创建接口缺少端口字段，可能导致同一IP地址下不同端口的设备无法正确区分。

处理过程：

1. 记录缺陷复现步骤、预期结果和实际结果。
2. 增加端口字段及1至65535范围校验。
3. 将重复规则调整为IP地址和端口组合校验。
4. 补充合法端口、边界值、重复组合等回归测试。
5. 回归测试全部通过，缺陷状态关闭。

详细记录：

`docs/03-缺陷报告-BUG-DEVICE-001.md`
