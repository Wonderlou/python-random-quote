# Let's Write a Python Quote Bot!

This repository will get you started with building a quote bot in Python. It's meant to be used along with the [Learning Lab](https://lab.github.com) intro to Python.

When complete, you'll be able to grab random quotes from the command line, like this:

> **$** python get-quote.py
>
> Keep it logically awesome
>
> **$** python get-quote.py
>
> Speak like a human

## Start the Tutorial

You can find your next step in [this repo's issues](../../issues/)!

---

## Bonus: 自动化执行购买任务脚本

仓库中新增了 `auto-purchase.py`，用于对接 HTTP API 自动执行购买流程（默认 **dry-run**，避免误下单）。

### 1) 准备配置

复制并修改示例配置文件：

```bash
cp purchase-config.example.json my-purchase-config.json
```

关键字段：

- `base_url`: 购买 API 地址
- `product_id`: 商品 ID
- `quantity`: 购买数量
- `max_price`: 最高可接受价格
- `timeout_seconds`: 脚本轮询超时时间
- `poll_interval_seconds`: 轮询间隔
- `auth_token_env`: API Token 的环境变量名

### 2) 设置 Token（可选）

```bash
export PURCHASE_API_TOKEN="your-token"
```

### 3) 先 dry-run

```bash
python auto-purchase.py --config my-purchase-config.json
```

### 4) 确认无误后真实执行

```bash
python auto-purchase.py --config my-purchase-config.json --execute
```

脚本会在每次轮询时检查库存和价格，满足条件后才会提交订单。
