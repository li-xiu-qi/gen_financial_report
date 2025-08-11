# Python 版搜索服务（search.py）说明文档

## 简介

本项目基于 FastAPI 和 Playwright 实现了与原版 Node.js `search.js` 类似的多站点网页搜索与抓取服务。支持多种搜索接口，具备缓存、错误处理等功能，适用于自动化信息采集、数据分析等场景。

## 主要特性

- 基于 FastAPI 提供高性能 Web API
- 使用 Playwright 实现浏览器自动化抓取
- 支持多站点搜索与内容提取
- 内置缓存机制，提升响应速度
- 详细的错误处理与日志输出

## 依赖环境

- Python 3.8 及以上
- 依赖包见 `requirements.txt`

## 安装步骤

1. 安装依赖包：

   ```bash
   pip install -r requirements.txt
   ```

2. 安装 Playwright 浏览器驱动：

   ```bash
   playwright install
   ```

## 启动服务

```bash
python search.py --port 30002
```

- 默认端口为 30002，可通过 `--port` 参数自定义。

## 主要接口说明

- `/help`：获取接口帮助文档
- `/search`：通用搜索接口，参数详见 `/help`
- `/bing`、`/google`、`/baidu` 等：各大搜索引擎专用接口
- `/cache`：缓存管理接口
- `/favicon`：获取网站 favicon


具体参数和返回格式请参考 `/help` 接口返回内容。

## 使用示例

假设服务已在本地 30002 端口启动，以下为常用接口的调用示例：

### 1. 获取帮助文档

```bash
curl http://localhost:30002/help
```

### 2. 必应搜索

```bash
curl "http://localhost:30002/bing?query=Python编程&total=3&cn=true"
```

### 3. 问财网搜索

```bash
curl "http://localhost:30002/iwencai?query=比亚迪"
```

### 4. 通用网页抓取

```bash
curl "http://localhost:30002/goto?query=https%3A%2F%2Fwww.baidu.com"
```

### 5. 外汇牌价

```bash
curl http://localhost:30002/whpj
```

如需更多参数和返回格式说明，请访问 `/help` 接口。

## 测试方法

1. 启动服务后，运行自动化测试脚本：

   ```bash
   python test_search.py
   ```

2. 也可使用 Postman、curl 等工具手动测试各接口。

## 常见问题

- **500 错误**：请检查依赖是否安装完整，Playwright 驱动是否安装，端口是否被占用。
- **Playwright 报错**：尝试重新执行 `playwright install`。
- **接口无响应**：检查 Python 版本、依赖包版本，或查看终端日志排查。

## 目录结构

```
search.py              # FastAPI 主程序
requirements.txt       # 依赖包列表
test_search.py         # 自动化测试脚本
setup.bat/start_search.bat # Windows 环境下的安装与启动脚本
```

## 参考

- [FastAPI 官方文档](https://fastapi.tiangolo.com/zh/)
- [Playwright for Python](https://playwright.dev/python/)

---
如有问题请先查阅本文件及 `/help` 接口，或反馈至项目维护者。
