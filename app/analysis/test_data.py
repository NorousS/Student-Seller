"""
Генератор синтетических тестовых данных для сравнения формул.

Типичные профили IT-студентов:
1. Backend Developer — акцент на Python, БД, алгоритмы
2. Data Scientist — акцент на ML, математику, анализ
3. DevOps Engineer — акцент на сети, ОС, безопасность
4. Full-stack — сбалансированный профиль
5. Теоретик — сильная математика, слабое программирование
"""

import random
from dataclasses import dataclass
from typing import Optional

from app.valuation import DisciplineWithGrade


# Типичные дисциплины IT-специальности
SAMPLE_DISCIPLINES = {
    "programming": [
        "Основы программирования",
        "Объектно-ориентированное программирование",
        "Программирование на Python",
        "Алгоритмы и структуры данных",
        "Web-программирование",
        "Программирование на Java",
        "Функциональное программирование",
    ],
    "databases": [
        "Базы данных",
        "Проектирование БД",
        "SQL и NoSQL системы",
        "Администрирование баз данных",
    ],
    "math": [
        "Математический анализ",
        "Линейная алгебра",
        "Теория вероятностей",
        "Дискретная математика",
        "Математическая статистика",
        "Численные методы",
    ],
    "systems": [
        "Операционные системы",
        "Компьютерные сети",
        "Информационная безопасность",
        "Архитектура компьютеров",
        "Системное администрирование",
    ],
    "ml_ai": [
        "Машинное обучение",
        "Искусственный интеллект",
        "Анализ данных",
        "Глубокое обучение",
        "Обработка естественного языка",
    ],
    "frontend": [
        "Веб-разработка",
        "JavaScript",
        "HTML и CSS",
        "React разработка",
        "UX/UI дизайн",
    ],
    "devops": [
        "Docker и контейнеризация",
        "CI/CD",
        "Kubernetes",
        "Облачные технологии",
        "Мониторинг и логирование",
    ],
}


@dataclass
class TestStudentProfile:
    """Профиль тестового студента."""
    
    name: str
    description: str
    disciplines: list[DisciplineWithGrade]
    expected_strength: str  # "weak", "average", "strong"


def _sample_disciplines(
    categories: list[str],
    weights: Optional[dict[str, float]] = None,
    count: int = 10,
    grade_mean: int = 4,
    grade_std: float = 0.5,
) -> list[DisciplineWithGrade]:
    """
    Выбирает случайные дисциплины из указанных категорий.
    
    Args:
        categories: Список категорий для выборки
        weights: Веса категорий (None = равномерно)
        count: Количество дисциплин
        grade_mean: Средняя оценка
        grade_std: Стандартное отклонение оценки
    """
    pool = []
    for cat in categories:
        if cat in SAMPLE_DISCIPLINES:
            for disc in SAMPLE_DISCIPLINES[cat]:
                weight = weights.get(cat, 1.0) if weights else 1.0
                pool.extend([disc] * int(weight * 10))
    
    if not pool:
        return []
    
    selected = random.sample(pool, min(count, len(pool)))
    # Убираем дубликаты
    selected = list(set(selected))[:count]
    
    disciplines = []
    for name in selected:
        # Генерируем оценку с нормальным распределением
        grade = round(random.gauss(grade_mean, grade_std))
        grade = max(3, min(5, grade))  # Ограничиваем 3-5
        disciplines.append(DisciplineWithGrade(name=name, grade=grade))
    
    return disciplines


def generate_backend_developer(
    strength: str = "average",
    count: int = 12,
) -> TestStudentProfile:
    """Генерирует профиль Backend-разработчика."""
    grade_mean = {"weak": 3.3, "average": 4.0, "strong": 4.7}[strength]
    
    disciplines = _sample_disciplines(
        categories=["programming", "databases", "systems"],
        weights={"programming": 2.0, "databases": 1.5, "systems": 1.0},
        count=count,
        grade_mean=grade_mean,
    )
    
    return TestStudentProfile(
        name=f"Backend Developer ({strength})",
        description="Акцент на Python, БД, алгоритмы",
        disciplines=disciplines,
        expected_strength=strength,
    )


def generate_data_scientist(
    strength: str = "average",
    count: int = 12,
) -> TestStudentProfile:
    """Генерирует профиль Data Scientist."""
    grade_mean = {"weak": 3.3, "average": 4.0, "strong": 4.7}[strength]
    
    disciplines = _sample_disciplines(
        categories=["ml_ai", "math", "programming"],
        weights={"ml_ai": 2.0, "math": 1.5, "programming": 1.0},
        count=count,
        grade_mean=grade_mean,
    )
    
    return TestStudentProfile(
        name=f"Data Scientist ({strength})",
        description="Акцент на ML, математику, анализ",
        disciplines=disciplines,
        expected_strength=strength,
    )


def generate_devops_engineer(
    strength: str = "average",
    count: int = 12,
) -> TestStudentProfile:
    """Генерирует профиль DevOps-инженера."""
    grade_mean = {"weak": 3.3, "average": 4.0, "strong": 4.7}[strength]
    
    disciplines = _sample_disciplines(
        categories=["devops", "systems", "programming"],
        weights={"devops": 2.0, "systems": 1.5, "programming": 1.0},
        count=count,
        grade_mean=grade_mean,
    )
    
    return TestStudentProfile(
        name=f"DevOps Engineer ({strength})",
        description="Акцент на сети, ОС, безопасность",
        disciplines=disciplines,
        expected_strength=strength,
    )


def generate_fullstack_developer(
    strength: str = "average",
    count: int = 15,
) -> TestStudentProfile:
    """Генерирует профиль Full-stack разработчика."""
    grade_mean = {"weak": 3.3, "average": 4.0, "strong": 4.7}[strength]
    
    disciplines = _sample_disciplines(
        categories=["programming", "frontend", "databases", "devops"],
        weights={"programming": 1.5, "frontend": 1.5, "databases": 1.0, "devops": 0.5},
        count=count,
        grade_mean=grade_mean,
    )
    
    return TestStudentProfile(
        name=f"Full-stack Developer ({strength})",
        description="Сбалансированный профиль",
        disciplines=disciplines,
        expected_strength=strength,
    )


def generate_theorist(
    strength: str = "average",
    count: int = 12,
) -> TestStudentProfile:
    """Генерирует профиль теоретика (сильная математика, слабое программирование)."""
    
    # У теоретика математика сильная, программирование слабое
    math_disciplines = _sample_disciplines(
        categories=["math"],
        count=count // 2,
        grade_mean=4.5 if strength == "strong" else 4.0,
    )
    
    prog_disciplines = _sample_disciplines(
        categories=["programming"],
        count=count // 2,
        grade_mean=3.3 if strength == "weak" else 3.7,
    )
    
    disciplines = math_disciplines + prog_disciplines
    
    return TestStudentProfile(
        name=f"Theorist ({strength})",
        description="Сильная математика, слабое программирование",
        disciplines=disciplines,
        expected_strength=strength,
    )


def generate_test_students(
    profiles_per_type: int = 3,
    seed: Optional[int] = None,
) -> dict[str, list[TestStudentProfile]]:
    """
    Генерирует набор тестовых студентов всех профилей.
    
    Returns:
        Словарь {profile_type: [profiles]}
    """
    if seed is not None:
        random.seed(seed)
    
    generators = {
        "backend": generate_backend_developer,
        "data_science": generate_data_scientist,
        "devops": generate_devops_engineer,
        "fullstack": generate_fullstack_developer,
        "theorist": generate_theorist,
    }
    
    result = {}
    
    for profile_type, generator in generators.items():
        profiles = []
        for strength in ["weak", "average", "strong"]:
            for _ in range(profiles_per_type):
                profiles.append(generator(strength=strength))
        result[profile_type] = profiles
    
    return result


def get_weak_students(
    test_students: dict[str, list[TestStudentProfile]],
) -> list[list[DisciplineWithGrade]]:
    """Извлекает слабых студентов для теста discrimination."""
    result = []
    for profiles in test_students.values():
        for profile in profiles:
            if profile.expected_strength == "weak":
                result.append(profile.disciplines)
    return result


def get_strong_students(
    test_students: dict[str, list[TestStudentProfile]],
) -> list[list[DisciplineWithGrade]]:
    """Извлекает сильных студентов для теста discrimination."""
    result = []
    for profiles in test_students.values():
        for profile in profiles:
            if profile.expected_strength == "strong":
                result.append(profile.disciplines)
    return result


def get_all_discipline_sets(
    test_students: dict[str, list[TestStudentProfile]],
) -> list[list[DisciplineWithGrade]]:
    """Извлекает все наборы дисциплин."""
    result = []
    for profiles in test_students.values():
        for profile in profiles:
            result.append(profile.disciplines)
    return result
