# 发给同事的安装 Prompt

复制以下整段到同事的 Codex。公开仓库可直接下载；企业数据仍须使用本人授权。

```text
请在这台 Windows 电脑安装“企业表图”插件。

安装仓库（只安装一次）：
https://github.com/EmilezCode/enterprise-table-chart

1. 检查 Git、Codex CLI、Python 3.11+ 是否可用。仓库已公开，正常下载不需要 GitHub 账号或仓库邀请。不要复制任何人的 Token，不安装无关软件。
2. 只检查我自己的 Codex 配置中是否存在 enterprise_data_remote 的 HTTPS 地址和 http_headers，不显示凭据。未配置时明确告诉我缺本人企业 MCP 授权并停在这里，不借用其他账号，也不猜服务器地址。
3. 将选定仓库克隆到我用户目录下的 EnterpriseTableChartSource（已存在时先核对仓库来源并保留本地修改，不能覆盖或删除），阅读 README.md 和 Install.ps1，再运行 powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1。安装范围仅为这个插件；不要改我的模型、记忆、其他 MCP 或权限设置。
4. 检查插件安装回执。已有旧版企业表图时提示我关闭旧版入口，避免重复。告诉我在新聊天里打开“企业表图”。未实际看到界面或查询成功时，不宣称同事端业务验收完成。

后续查询和图表的兼容服务端更新无需重装。客户端文件确实变化时才运行仓库内 Update.ps1；不建立定时更新或后台监控。
```
