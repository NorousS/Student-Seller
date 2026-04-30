import pytest

from app.routers.employer import _build_discipline_groups
from app.schemas import DisciplineResponse


@pytest.mark.no_db
def test_build_discipline_groups_orders_and_averages():
    disciplines = [
        DisciplineResponse(id=1, name="Lean менеджмент", grade=5, category="Soft skills"),
        DisciplineResponse(id=2, name="Python", grade=5, category="Программирование"),
        DisciplineResponse(id=3, name="Java", grade=4, category="Программирование"),
        DisciplineResponse(id=4, name="Физика", grade=3, category="Точные науки"),
    ]

    groups = _build_discipline_groups(disciplines)

    assert [group.group_name for group in groups] == [
        "Программирование",
        "Soft skills",
        "Точные науки",
    ]
    programming = groups[0]
    assert programming.total_count == 2
    assert programming.avg_grade == 4.5
    assert [discipline.name for discipline in programming.disciplines] == ["Python", "Java"]
