# R03 禁止 fall-back（强制）

失败即 raise，禁止任何静默兜底和假数据。

- 业务错误必须 `raise` 明确异常
- 禁止 `except: pass` / `return None` / `return []`
- 跑不通就是业务设计有问题，返回告警即可
- 禁止用假数据"让程序跑通"
