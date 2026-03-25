"""
Простой API-тест для выбора наилучшей формулы через эндпоинт /api/v1/analysis/evaluate-formulas
"""

import httpx
import json
import sys

BASE_URL = "http://127.0.0.1:8000"


def register_admin():
    """Регистрирует админа и возвращает токен."""
    response = httpx.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "email": "test_admin@example.com",
            "password": "AdminPass123!!",
            "role": "admin"
        }
    )
    
    if response.status_code == 201:
        token = response.json()["access_token"]
        print(f"✅ Админ зарегистрирован, токен получен")
        return token
    elif response.status_code == 400 and "already registered" in response.text:
        # Логин если уже существует
        response = httpx.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "email": "test_admin@example.com",
                "password": "AdminPass123!!"
            }
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"✅ Админ залогинен, токен получен")
            return token
    
    print(f"❌ Ошибка регистрации/логина: {response.text}")
    return None


def create_test_student(token):
    """Создает тестового студента с дисциплинами."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Создаем студента
    student_response = httpx.post(
        f"{BASE_URL}/api/v1/students",
        json={
            "email": "test_student@example.com",
            "password": "Student123!!",
            "full_name": "Иван Иванов",
            "university": "МГУ",
            "specialty": "Python Backend Developer"
        },
        headers=headers
    )
    
    if student_response.status_code not in (200, 201):
        print(f"❌ Ошибка создания студента: {student_response.text}")
        # Попробуем получить существующего
        students_response = httpx.get(
            f"{BASE_URL}/api/v1/students",
            headers=headers
        )
        if students_response.status_code == 200:
            students = students_response.json()
            if students:
                student_id = students[0]["id"]
                print(f"✅ Используем существующего студента ID={student_id}")
                return student_id
        return None
    
    student_id = student_response.json()["id"]
    print(f"✅ Студент создан, ID={student_id}")
    
    # Добавляем дисциплины
    disciplines = [
        {"name": "Программирование на Python", "grade": 5},
        {"name": "Базы данных", "grade": 5},
        {"name": "Алгоритмы и структуры данных", "grade": 4},
        {"name": "Web-программирование", "grade": 5},
        {"name": "Математический анализ", "grade": 4},
        {"name": "Операционные системы", "grade": 4},
        {"name": "Компьютерные сети", "grade": 5},
    ]
    
    for disc in disciplines:
        disc_response = httpx.post(
            f"{BASE_URL}/api/v1/students/{student_id}/disciplines",
            json=disc,
            headers=headers
        )
        if disc_response.status_code not in (200, 201):
            print(f"⚠️  Ошибка добавления дисциплины {disc['name']}")
    
    print(f"✅ Добавлено {len(disciplines)} дисциплин")
    return student_id


def list_formulas(token):
    """Получает список доступных формул."""
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(
        f"{BASE_URL}/api/v1/analysis/formulas",
        headers=headers
    )
    
    if response.status_code == 200:
        formulas = response.json()
        print(f"\n📐 Доступно формул: {len(formulas)}")
        for formula in formulas:
            print(f"   • {formula['name']}: {formula['description']}")
        return formulas
    else:
        print(f"❌ Ошибка получения формул: {response.text}")
        return []


def evaluate_formulas(token, student_ids):
    """Вызывает эндпоинт для оценки всех формул."""
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.post(
        f"{BASE_URL}/api/v1/analysis/evaluate-formulas",
        json={"test_student_ids": student_ids},
        headers=headers
    )
    
    if response.status_code == 200:
        results = response.json()
        print(f"\n📊 Результаты анализа формул:")
        print("=" * 70)
        
        for formula_name, metrics in results.items():
            print(f"\n{formula_name.upper()}:")
            print(f"  Stability: {metrics['stability_score']:.3f}")
            print(f"  Consistency: {metrics['consistency_score']:.3f}")
            print(f"  Coverage: {metrics['coverage_ratio']:.3f}")
            print(f"  Discrimination: {metrics['discrimination_power']:.3f}")
        
        # Выбираем лучшую формулу
        best_formula = max(
            results.items(),
            key=lambda x: (
                0.3 * x[1]["stability_score"] +
                0.3 * x[1]["discrimination_power"] +
                0.2 * x[1]["consistency_score"] +
                0.2 * x[1]["coverage_ratio"]
            )
        )
        
        print("\n" + "=" * 70)
        print(f"🏆 РЕКОМЕНДУЕМАЯ ФОРМУЛА: {best_formula[0]}")
        print(f"   Composite Score: {0.3 * best_formula[1]['stability_score'] + 0.3 * best_formula[1]['discrimination_power'] + 0.2 * best_formula[1]['consistency_score'] + 0.2 * best_formula[1]['coverage_ratio']:.3f}")
        print("=" * 70)
        
        # Сохраняем результаты
        with open("formula_evaluation_results.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "all_results": results,
                    "best_formula": best_formula[0],
                    "recommendation": {
                        "formula": best_formula[0],
                        "metrics": best_formula[1],
                        "reasoning": "Выбрана на основе комплексного анализа: 30% stability + 30% discrimination + 20% consistency + 20% coverage"
                    }
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        print("\n💾 Результаты сохранены в formula_evaluation_results.json")
        
        return best_formula[0]
    else:
        print(f"❌ Ошибка оценки формул: {response.text}")
        return None


def main():
    print("=" * 70)
    print("ВЫБОР НАИЛУЧШЕЙ ФОРМУЛЫ ОЦЕНКИ СТУДЕНТОВ")
    print("Метод: API-эндпоинт /api/v1/analysis/evaluate-formulas")
    print("=" * 70)
    
    # 1. Получаем токен админа
    token = register_admin()
    if not token:
        print("❌ Не удалось получить токен админа")
        sys.exit(1)
    
    # 2. Создаем тестового студента
    student_id = create_test_student(token)
    if not student_id:
        print("❌ Не удалось создать студента")
        sys.exit(1)
    
    # 3. Получаем список формул
    formulas = list_formulas(token)
    if not formulas:
        print("❌ Нет доступных формул")
        sys.exit(1)
    
    # 4. Запускаем оценку всех формул
    best_formula = evaluate_formulas(token, [student_id])
    
    if best_formula:
        print(f"\n✅ Анализ завершен! Рекомендуется использовать: {best_formula}")
    else:
        print("\n❌ Не удалось выполнить анализ формул")
        sys.exit(1)


if __name__ == "__main__":
    main()
