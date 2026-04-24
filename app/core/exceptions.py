class DomainError(Exception):
    """业务层基础异常，所有领域异常均继承此类。"""


class ConflictError(DomainError):
    """资源冲突异常，例如唯一键重复。"""
