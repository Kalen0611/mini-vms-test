# BUG-DEVICE-001 设备端口字段缺失

## 1. 缺陷信息

- 缺陷编号：BUG-DEVICE-001
- 缺陷标题：添加设备接口未保存和校验端口字段
- 关联需求：REQ-DEVICE-001、REQ-DEVICE-004、REQ-DEVICE-005
- 所属模块：设备管理
- 严重程度：S2 严重
- 优先级：P1 高
- 当前状态：新建
- 发现阶段：功能测试

## 2. 测试环境

- 操作系统：macOS
- Python版本：3.14.4
- Web框架：FastAPI
- 测试环境：本地开发环境
- 测试接口：POST /api/devices

## 3. 前置条件

MiniVMS服务已经启动，并且可以正常访问Swagger接口文档。

## 4. 复现步骤

1. 打开Swagger接口文档。
2. 找到POST /api/devices接口。
3. 输入合法设备名称、IP地址、端口和设备类型。
4. 点击Execute发送请求。
5. 查看接口响应内容。
6. 将端口改为0，再次发送请求。

## 5. 测试数据

```json
{
  "name": "端口测试摄像机",
  "ip_address": "192.168.1.110",
  "port": 8000,
  "device_type": "网络摄像机"
}