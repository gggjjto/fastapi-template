from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CustomModel(BaseModel):
    """所有 Pydantic Schema 的全局基类，统一配置序列化行为。"""

    model_config = ConfigDict(
        populate_by_name=True,  # 允许同时使用字段名和别名赋值
        from_attributes=True,  # 支持从 ORM 对象直接构造（model_validate）
    )
