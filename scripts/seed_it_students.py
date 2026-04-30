"""Seed demo KAI IT students with disciplines.

Run from Docker after the database is up:
    docker compose run --rm app uv run python scripts/seed_it_students.py --count 18

Useful checks:
    docker compose run --rm app uv run python scripts/seed_it_students.py --list-programs
    docker compose run --rm app uv run python scripts/seed_it_students.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from itertools import cycle

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker, create_tables
from app.discipline_groups import OTHER, infer_discipline_group
from app.models import Discipline, Student, StudentDiscipline


@dataclass(frozen=True)
class ItProgram:
    education_type: str
    code: str
    name: str
    href: str
    track: str


IT_PROGRAMS: tuple[ItProgram, ...] = (
    ItProgram(
        "Бакалавриат",
        "01.03.02 Прикладная математика и информатика",
        "Модели и анализ больших данных (BigData)",
        "https://abiturientu.kai.ru/01.03.02",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Бакалавриат",
        "09.03.01 Информатика и вычислительная техника",
        "Программирование и администрирование компьютерных систем",
        "https://abiturientu.kai.ru/09.03.01",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Бакалавриат",
        "09.03.02 Информационные системы и технологии",
        "Интеллектуальные информационные системы",
        "https://abiturientu.kai.ru/09.03.02",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Бакалавриат",
        "09.03.03 Прикладная информатика",
        "Робототехника и цифровая экономика",
        "https://abiturientu.kai.ru/09.03.03",
        "Робототехника и беспилотные системы; Экономика и управление",
    ),
    ItProgram(
        "Бакалавриат",
        "09.03.04 Программная инженерия",
        "Программная инженерия",
        "https://abiturientu.kai.ru/09.03.04",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Бакалавриат",
        "10.03.01 Информационная безопасность",
        "Информационная безопасность",
        "https://abiturientu.kai.ru/10.03.01",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Специалитет",
        "10.05.02 Информационная безопасность телекоммуникационных систем",
        "Защита информации в компьютерных сетях",
        "https://abiturientu.kai.ru/10.05.02",
        "Программирование, искусственный интеллект и информационная безопасность; Умный дом и интернет вещей",
    ),
    ItProgram(
        "Бакалавриат",
        "09.03.01 Информатика и вычислительная техника",
        "Прикладные информационные технологии в технологическом предпринимательстве",
        "https://abiturientu.kai.ru/09.03.01_1",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "СПО",
        "09.02.06 Сетевое и системное администрирование",
        "09.02.06 Сетевое и системное администрирование (на базе 9 классов)",
        "https://abiturientu.kai.ru/09.02.06",
        "Информатика и ИКТ",
    ),
    ItProgram(
        "СПО",
        "09.02.08 Интеллектуальные интегрированные системы",
        "09.02.08 Интеллектуальные интегрированные системы (на базе 9 классов)",
        "https://abiturientu.kai.ru/09.02.08",
        "Информатика и ИКТ",
    ),
    ItProgram(
        "СПО",
        "09.02.11 Разработка и управление программным обеспечением",
        "09.02.11 Разработка и управление программным обеспечением (на базе 9 классов)",
        "https://abiturientu.kai.ru/09.02.11",
        "Информатика и ИКТ",
    ),
    ItProgram(
        "СПО",
        "09.02.12 Техническая эксплуатация и сопровождение информационных систем",
        "09.02.12 Техническая эксплуатация и сопровождение информационных систем (на базе 9 классов)",
        "https://abiturientu.kai.ru/09.02.12",
        "Информатика и ИКТ",
    ),
    ItProgram(
        "СПО",
        "10.02.05 Обеспечение информационной безопасности автоматизированных систем",
        "10.02.05 Обеспечение информационной безопасности автоматизированных систем (на базе 9 классов)",
        "https://abiturientu.kai.ru/10.02.05",
        "Информатика и ИКТ",
    ),
    ItProgram(
        "Магистратура",
        "01.04.02 Прикладная математика и информатика",
        "01.04.02 Прикладная математика и информатика",
        "https://abiturientu.kai.ru/01.04.02",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Магистратура",
        "09.04.01 Информатика и вычислительная техника",
        "09.04.01 Информатика и вычислительная техника",
        "https://abiturientu.kai.ru/09.04.01",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Магистратура",
        "09.04.02 Информационные системы и технологии",
        "09.04.02 Информационные системы и технологии",
        "https://abiturientu.kai.ru/09.04.02",
        "Программирование, искусственный интеллект и информационная безопасность",
    ),
    ItProgram(
        "Магистратура",
        "09.04.03 Прикладная информатика",
        "09.04.03 Прикладная информатика",
        "https://abiturientu.kai.ru/09.04.03",
        "Программирование, искусственный интеллект и информационная безопасность; Экономика и управление",
    ),
    ItProgram(
        "Магистратура",
        "12.04.03 Фотоника и оптоинформатика",
        "12.04.03 Фотоника и оптоинформатика",
        "https://abiturientu.kai.ru/12.04.03",
        "Информатика и ИКТ",
    ),
)


COMMON_DISCIPLINES: tuple[str, ...] = (
    "Python",
    "Java",
    "Алгоритмы и структуры данных",
    "Базы данных",
    "Операционные системы",
    "Компьютерные сети",
    "Английский язык",
    "Soft skills в IT",
    "Управление IT проектами",
    "Линейная алгебра",
    "Математический анализ",
    "Теория вероятностей и математическая статистика",
)

PROGRAM_DISCIPLINES: dict[str, tuple[str, ...]] = {
    "bigdata": (
        "Машинное обучение",
        "Анализ данных",
        "Big Data",
        "Python для анализа данных",
    ),
    "администрирование": ("Linux", "Администрирование серверов", "Docker", "DevOps"),
    "интеллектуальные информационные": (
        "Искусственный интеллект",
        "Проектирование информационных систем",
        "Web-разработка",
    ),
    "робототехника": (
        "Робототехника",
        "Интернет вещей",
        "Основы цифровой экономики",
        "Lean менеджмент",
    ),
    "программная инженерия": (
        "Git",
        "Тестирование ПО",
        "Архитектура ПО",
        "Backend-разработка",
    ),
    "информационная безопасность": (
        "Криптография",
        "Безопасность сетей",
        "Защита информации",
        "Администрирование Linux",
    ),
    "компьютерных сетях": (
        "Компьютерные сети",
        "Сетевая безопасность",
        "Телекоммуникационные системы",
    ),
    "предпринимательстве": (
        "Технологическое предпринимательство",
        "Web-разработка",
        "Управление IT проектами",
    ),
    "системное администрирование": (
        "Linux",
        "Компьютерные сети",
        "Администрирование серверов",
    ),
    "разработка и управление программным обеспечением": (
        "Python",
        "JavaScript",
        "Тестирование ПО",
        "Управление IT проектами",
    ),
    "сопровождение информационных систем": (
        "SQL",
        "Техническая поддержка информационных систем",
        "Документирование ПО",
    ),
    "автоматизированных систем": (
        "Информационная безопасность",
        "Безопасность сетей",
        "Криптография",
    ),
    "фотоника": (
        "Оптоинформатика",
        "Физика",
        "Информатика",
        "Математическое моделирование",
    ),
}

NAMES: tuple[str, ...] = (
    "Алексей Морозов",
    "Мария Кузнецова",
    "Данил Сафин",
    "Алина Нуриева",
    "Илья Волков",
    "София Сергеева",
    "Тимур Галеев",
    "Виктория Павлова",
    "Кирилл Андреев",
    "Дарья Иванова",
    "Роман Федоров",
    "Эльвира Каримова",
    "Никита Егоров",
    "Полина Захарова",
    "Артур Хабибуллин",
    "Екатерина Орлова",
    "Марат Сабиров",
    "Анна Белова",
)


def program_group(program: ItProgram) -> str:
    code = program.code.split()[0].replace(".", "")
    if program.education_type == "СПО":
        return f"СПО-{code[:4]}"
    if program.education_type == "Магистратура":
        return f"М{code[:4]}-ИТ"
    return f"{code[:4]}-ИТ"


def program_specific_disciplines(program: ItProgram) -> tuple[str, ...]:
    haystack = f"{program.name} {program.code}".lower()
    for marker, disciplines in PROGRAM_DISCIPLINES.items():
        if marker in haystack:
            return disciplines
    return ("Информатика", "Программирование", "Проектная деятельность")


def build_disciplines(program: ItProgram, index: int) -> list[tuple[str, int]]:
    names = list(COMMON_DISCIPLINES[:8]) + list(program_specific_disciplines(program))
    if index % 3 == 0:
        names.extend(["Немецкий язык", "Основы психологии"])
    if index % 2 == 0:
        names.extend(["Матан", "Физика"])

    unique_names = list(dict.fromkeys(names))
    grades = cycle((5, 5, 4, 5, 4, 5, 3))
    return [(name, next(grades)) for name in unique_names]


async def get_or_create_discipline(session, name: str) -> Discipline:
    result = await session.execute(select(Discipline).where(Discipline.name == name))
    discipline = result.scalar_one_or_none()
    if discipline is None:
        inferred_category = infer_discipline_group(name)
        discipline = Discipline(
            name=name,
            category=inferred_category if inferred_category != OTHER else None,
        )
        session.add(discipline)
        await session.flush()
    return discipline


def student_name(base_name: str, index: int) -> str:
    if index <= len(NAMES):
        return base_name
    return f"{base_name} {index}"


async def seed_student(
    program: ItProgram, full_name: str, index: int
) -> tuple[int, bool, int]:
    marker = f"KAI IT seed #{index}: {program.href}"
    legacy_marker = f"KAI IT seed: {program.href}"
    disciplines = build_disciplines(program, index)

    async with async_session_maker() as session:
        result = await session.execute(
            select(Student)
            .options(selectinload(Student.student_disciplines))
            .where(Student.about_me.in_([marker, legacy_marker]))
        )
        student = result.scalar_one_or_none()
        created = student is None

        if student is None:
            student = Student(
                full_name=full_name, group_name=program_group(program), about_me=marker
            )
            session.add(student)
            await session.flush()
        else:
            student.full_name = full_name
            student.group_name = program_group(program)
            student.about_me = marker

        for discipline_name, grade in disciplines:
            discipline = await get_or_create_discipline(session, discipline_name)
            link_result = await session.execute(
                select(StudentDiscipline).where(
                    StudentDiscipline.student_id == student.id,
                    StudentDiscipline.discipline_id == discipline.id,
                )
            )
            link = link_result.scalar_one_or_none()
            if link is None:
                session.add(
                    StudentDiscipline(
                        student_id=student.id, discipline_id=discipline.id, grade=grade
                    )
                )
            else:
                link.grade = grade

        await session.commit()
        return student.id, created, len(disciplines)


def selected_programs(count: int) -> list[ItProgram]:
    if count < 1:
        raise ValueError("--count must be >= 1")
    return [IT_PROGRAMS[index % len(IT_PROGRAMS)] for index in range(count)]


def print_programs() -> None:
    for index, program in enumerate(IT_PROGRAMS, start=1):
        print(
            f"{index:02d}. {program.education_type} | {program.code} | {program.name} | {program.href}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed KAI IT students with realistic disciplines."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=len(IT_PROGRAMS),
        help="Number of students to create/update.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned students without touching the DB.",
    )
    parser.add_argument(
        "--list-programs",
        action="store_true",
        help="Print extracted IT programs and exit.",
    )
    args = parser.parse_args()

    if args.list_programs:
        print_programs()
        return

    programs = selected_programs(args.count)
    if args.dry_run:
        for index, (program, base_name) in enumerate(
            zip(programs, cycle(NAMES)), start=1
        ):
            full_name = student_name(base_name, index)
            discipline_names = ", ".join(
                name for name, _grade in build_disciplines(program, index)
            )
            print(
                f"{index:02d}. {full_name} | {program_group(program)} | {program.name}"
            )
            print(f"    {discipline_names}")
        return

    await create_tables()

    created_count = 0
    updated_count = 0
    for index, (program, base_name) in enumerate(zip(programs, cycle(NAMES)), start=1):
        full_name = student_name(base_name, index)
        student_id, created, disciplines_count = await seed_student(
            program, full_name, index
        )
        created_count += int(created)
        updated_count += int(not created)
        action = "created" if created else "updated"
        print(
            f"{action}: student_id={student_id} name={full_name!r} "
            f"group={program_group(program)} disciplines={disciplines_count}"
        )

    print(
        f"Done: created={created_count}, updated={updated_count}, total={len(programs)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
