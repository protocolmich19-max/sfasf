"""
Утилиты для работы с реферальной системой
"""
from typing import Optional


def get_ref_level_requirement(line: int) -> int:
    """
    Определяет минимальный уровень партнерской программы для получения бонуса в указанной линии.
    
    Args:
        line: Номер линии (1-20)
        
    Returns:
        Минимальный требуемый уровень партнерской программы
    """
    if line == 1:
        return 1
    if line in (2, 3):
        return 2
    if line in (4, 5):
        return 3
    if line in (6, 7):
        return 4
    if line in (8, 9):
        return 5
    if line > 9:
        return 6
    return 1


def get_ref_percent(line: int) -> float:
    """
    Возвращает процент от суммы платежа, который начисляется рефереру в указанной линии.
    
    Args:
        line: Номер линии (1-20)
        
    Returns:
        Процент от суммы платежа
    """
    percentages = {
        1: 40.0,
        2: 20.0,
        3: 14.0,
        4: 6.0,
        5: 6.0,
        6: 4.0,
        7: 4.0,
        8: 3.0,
        9: 2.0,
        10: 0.5,
        11: 0.25,
        12: 0.125,
        13: 0.0625,
        14: 0.03125,
        15: 0.015625,
        16: 0.0078125,
        17: 0.00390625,
        18: 0.001953125,
        19: 0.0009765625,
        20: 0.00048828125,
    }
    return percentages.get(line, 0.0)


def get_ref_inner_percent(line: int) -> float:
    """
    Возвращает процент от внутреннего баланса, который начисляется рефереру в указанной линии.
    
    Args:
        line: Номер линии (1-20)
        
    Returns:
        Процент от внутреннего баланса
    """
    if line == 1:
        return 40.0
    if line == 2:
        return 40.0
    if line == 3:
        return 20.0
    return 0.0

