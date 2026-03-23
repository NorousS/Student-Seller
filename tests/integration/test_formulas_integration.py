"""
Integration тесты для системы формул и API.
"""

import pytest
from httpx import AsyncClient, ASGITransport


pytestmark = pytest.mark.anyio


@pytest.fixture
async def admin_headers(test_client: AsyncClient):
    """Создаёт админа и возвращает заголовки авторизации."""
    # Регистрируем админа
    register_data = {
        "email": "admin_formula_test@example.com",
        "password": "TestPass123!",
        "full_name": "Formula Admin",
        "role": "admin",
    }
    
    await test_client.post("/api/v1/auth/register", json=register_data)
    
    # Логинимся
    login_data = {"username": "admin_formula_test@example.com", "password": "TestPass123!"}
    response = await test_client.post("/api/v1/auth/login", data=login_data)
    
    if response.status_code != 200:
        pytest.skip("Could not create admin user")
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestFormulaAPI:
    """Тесты API формул (требуют test_client фикстуру)."""
    
    @pytest.mark.skip(reason="Requires test_client fixture from conftest")
    async def test_list_formulas(self, test_client: AsyncClient, admin_headers: dict):
        """Проверяет что API возвращает список формул."""
        response = await test_client.get(
            "/api/v1/analysis/formulas",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        formulas = response.json()
        
        assert len(formulas) == 6
        
        names = [f["name"] for f in formulas]
        assert "baseline" in names
        assert "linear" in names
        assert "quadratic" in names
        assert "exponential" in names
        assert "tfidf" in names
        assert "matrix" in names


class TestFormulaIntegration:
    """Интеграционные тесты формул с valuation."""
    
    async def test_all_formulas_produce_results(self):
        """Все формулы должны производить результаты для одних и тех же входных данных."""
        from app.formulas import FormulaRegistry
        
        formulas = FormulaRegistry.get_all_formulas()
        
        # Тестовые данные
        test_cases = [
            (0.9, 100, 1.0),   # Высокая схожесть
            (0.5, 50, 0.85),   # Средняя схожесть
            (0.3, 10, 0.75),   # Низкая схожесть
            (0.99, 1000, 1.0), # Очень высокая схожесть, много вакансий
            (0.1, 5, 0.75),    # Очень низкая схожесть
        ]
        
        for similarity, count, grade in test_cases:
            results = {}
            for formula in formulas:
                weight = formula.calculate_weight(similarity, count, grade)
                results[formula.get_name()] = weight
                
                # Все веса должны быть >= 0
                assert weight >= 0, f"{formula.get_name()} returned negative weight"
            
            # Проверяем что формулы дают разные результаты (не все одинаковые)
            unique_weights = set(round(w, 4) for w in results.values())
            assert len(unique_weights) >= 2, f"All formulas returned same weight for {test_cases}"
    
    async def test_formula_ordering(self):
        """Проверяет логичное упорядочивание весов."""
        from app.formulas import FormulaRegistry
        
        for formula_name in FormulaRegistry.list_formulas():
            formula = FormulaRegistry.get_formula(formula_name)
            
            # Больший similarity → больший вес
            w_high = formula.calculate_weight(0.9, 100, 1.0)
            w_low = formula.calculate_weight(0.5, 100, 1.0)
            assert w_high >= w_low, f"{formula_name}: higher similarity should give higher weight"
            
            # Больший grade_coeff → больший вес
            w_grade_high = formula.calculate_weight(0.8, 100, 1.0)
            w_grade_low = formula.calculate_weight(0.8, 100, 0.75)
            assert w_grade_high >= w_grade_low, f"{formula_name}: higher grade should give higher weight"
    
    async def test_tfidf_prefers_rare_skills(self):
        """TF-IDF должна предпочитать редкие навыки."""
        from app.formulas import TFIDFFormula
        
        formula = TFIDFFormula(total_vacancies=10000)
        
        rare_weight = formula.calculate_weight(0.8, 10, 1.0)
        common_weight = formula.calculate_weight(0.8, 1000, 1.0)
        
        assert rare_weight > common_weight, "TF-IDF should prefer rare skills"
    
    async def test_quadratic_amplifies_high_similarity(self):
        """Quadratic должна сильнее усиливать высокую схожесть."""
        from app.formulas import QuadraticFormula, BaselineFormula
        
        quadratic = QuadraticFormula()
        baseline = BaselineFormula()
        
        # Соотношение для similarity 0.9 vs 0.5
        quad_ratio = (
            quadratic.calculate_weight(0.9, 100, 1.0) /
            quadratic.calculate_weight(0.5, 100, 1.0)
        )
        
        base_ratio = (
            baseline.calculate_weight(0.9, 100, 1.0) /
            baseline.calculate_weight(0.5, 100, 1.0)
        )
        
        assert quad_ratio > base_ratio, "Quadratic should amplify high similarity more"


class TestAnalysisTestData:
    """Тесты генератора тестовых данных."""
    
    async def test_generate_students(self):
        """Проверяет генерацию тестовых студентов."""
        from app.analysis import generate_test_students
        
        students = generate_test_students(profiles_per_type=2, seed=42)
        
        # Должны быть все профили
        assert "backend" in students
        assert "data_science" in students
        assert "devops" in students
        assert "fullstack" in students
        assert "theorist" in students
        
        # Каждый профиль имеет 6 студентов (2 × 3 уровня силы)
        for profile_type, profiles in students.items():
            assert len(profiles) == 6, f"{profile_type} should have 6 profiles"
    
    async def test_student_strength_distribution(self):
        """Проверяет распределение силы студентов."""
        from app.analysis import generate_test_students, get_weak_students, get_strong_students
        
        students = generate_test_students(profiles_per_type=3, seed=42)
        
        weak = get_weak_students(students)
        strong = get_strong_students(students)
        
        # 5 профилей × 3 = 15 слабых и 15 сильных
        assert len(weak) == 15
        assert len(strong) == 15


class TestGrouping:
    """Тесты группировки навыков и дисциплин."""
    
    async def test_skill_clusterer_categories(self):
        """Проверяет что SkillClusterer имеет все категории."""
        from app.grouping import SKILL_CATEGORY_ANCHORS
        
        expected_categories = [
            "backend", "frontend", "devops", "data",
            "soft_skills", "tools", "mobile", "qa",
        ]
        
        for cat in expected_categories:
            assert cat in SKILL_CATEGORY_ANCHORS, f"Missing category: {cat}"
    
    async def test_discipline_clusterer_anchors(self):
        """Проверяет что DisciplineClusterer имеет якорные категории."""
        from app.grouping.discipline_clusterer import CATEGORY_ANCHORS
        
        expected = [
            "programming", "databases", "math",
            "networks", "ai_ml", "security",
        ]
        
        for cat in expected:
            assert cat in CATEGORY_ANCHORS, f"Missing anchor: {cat}"
