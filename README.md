# 家族谱系管理系统 (Family Genealogy System)

基于 Flask + SQLite/PostgreSQL 的家族谱系管理系统，支持多用户、多家族、复杂血缘关系查询与可视化。

## 快速启动

### Windows
双击 `RUN.bat` 或执行：
```bash
python -m pip install flask flask-sqlalchemy flask-cors pyjwt bcrypt --user
python init_db.py
python app.py
```

浏览器访问 **http://localhost:5000**

### 生成模拟数据
```bash
# 少量测试数据（2个家族，各200人）
python generate_data.py --families 2 --members 200

# 大规模数据（10个家族，各5000人）
python generate_data.py --families 10 --members 5000
```

### 使用 PostgreSQL（可选）
```bash
# 1. 先执行 schema.sql 创建表结构
psql -U postgres -d your_db -f schema.sql

# 2. 设置环境变量
set DATABASE_URL=postgresql://postgres:password@localhost:5432/your_db
python app.py
```

## 测试账户

数据生成后可使用：
- 用户名: `demo` / 密码: `demo123`

或自行注册新账户。

## 功能列表

| 功能 | 说明 |
|------|------|
| 用户注册/登录 | JWT 认证，数据隔离 |
| 家族管理 | 创建、编辑、删除家族 |
| 成员管理 | CRUD + 模糊搜索 + 分页 + 筛选 |
| 祖先追溯 | 递归 CTE，支持限制深度 |
| 后代展开 | 递归 CTE，树形展示 |
| 血缘路径查询 | 两人共同祖先 + 关系路径图 |
| 家族树可视化 | ECharts 树图，可展开/折叠 |
| 统计报表 | 各代人数、性别构成、平均寿命 |
| Dashboard | 概览面板 + 性别比例饼图 |

## 项目结构

```
family_genealogy/
├── app.py              # Flask 应用入口
├── config.py           # 配置
├── models.py           # SQLAlchemy 数据模型
├── auth.py             # JWT 认证
├── init_db.py          # 数据库初始化
├── generate_data.py    # 模拟数据生成器
├── schema.sql          # PostgreSQL 参考 DDL
├── requirements.txt    # 依赖列表
├── RUN.bat             # Windows 一键启动
├── routes/
│   ├── __init__.py     # 路由注册
│   ├── auth_routes.py  # 认证 API
│   ├── family_routes.py# 家族 CRUD API
│   ├── member_routes.py# 成员 CRUD + 递归查询 API
│   ├── relation_routes.py # 关系 + 血缘路径 API
│   └── stats_routes.py # 统计 API
├── templates/          # Jinja2 前端模板
│   ├── base.html       # 基础布局（侧边栏+导航）
│   ├── login.html      # 登录页
│   ├── register.html   # 注册页
│   ├── dashboard.html  # 仪表盘
│   ├── families.html   # 家族列表
│   ├── member_list.html# 成员列表
│   ├── member_detail.html # 成员详情
│   ├── member_form.html# 添加/编辑成员
│   ├── family_tree.html# 家族树可视化
│   ├── relation_path.html # 血缘路径查询
│   └── stats.html      # 统计报表
└── static/
    ├── css/style.css   # 自定义样式
    └── js/app.js       # 前端工具函数
```

## 关键技术

- **递归 CTE**：祖先追溯、后代展开、血缘路径搜索
- **循环检测**：路径数组跟踪，防止无限递归
- **索引优化**：parent_id / child_id B-Tree 索引覆盖递归 JOIN
- **JWT 认证**：无状态会话 + 数据隔离
- **ECharts**：树图(graph/tree) + 柱状图 + 折线图 + 饼图
