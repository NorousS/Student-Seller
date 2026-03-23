"""
Unit тесты для всех формул расчёта веса.
"""

import math

import pytest

from app.formulas import (
    FormulaRegistry,
    BaselineFormula,
    LinearFormula,
    QuadraticFormula,
    ExponentialFormula,
    TFIDFFormula,
    MatrixFormula,
)


class TestBaselineFormula:
    """Тесты F1: Baseline."""
    
    def test_basic_calculation(self):
        formula = BaselineFormula()
        
        weight = formula.calculate_weight(
            similarity=0.8,
            vacancy_count=100,
            grade_coeff=1.0,
        )
        
        expected = 0.8 * math.log1p(100) * 1.0
        assert abs(weight - expected) < 0.001
    
    def test_zero_count(self):
        formula = BaselineFormula()
        weight = formula.calculate_weight(0.9, 0, 1.0)
        assert weight == 0.0
    
    def test_grade_coefficient(self):
        formula = BaselineFormula()
        
        w_low = formula.calculate_weight(0.8, 100, 0.75)
        w_high = formula.calculate_weight(0.8, 100, 1.0)
        
        assert w_high > w_low
        assert abs(w_high / w_low - 1.0 / 0.75) < 0.001
    
    def test_name(self):
        assert BaselineFormula().get_name() == "baseline"


class TestLinearFormula:
    """Тесты F2: Linear."""
    
    def test_basic_calculation(self):
        formula = LinearFormula(max_count=1000)
        
        weight = formula.calculate_weight(
            similarity=0.8,
            vacancy_count=500,
            grade_coeff=1.0,
        )
        
        # 0.8 * (500/1000) * 1.0 = 0.4
        assert abs(weight - 0.4) < 0.001
    
    def test_capped_at_max(self):
        formula = LinearFormula(max_count=100)
        
        w1 = formula.calculate_weight(0.8, 100, 1.0)
        w2 = formula.calculate_weight(0.8, 200, 1.0)
        
        # Должны быть равны - cap на max_count
        assert abs(w1 - w2) < 0.001
    
    def test_name(self):
        assert LinearFormula().get_name() == "linear"


class TestQuadraticFormula:
    """Тесты F3: Quadratic."""
    
    def test_basic_calculation(self):
        formula = QuadraticFormula()
        
        weight = formula.calculate_weight(
            similarity=0.8,
            vacancy_count=100,
            grade_coeff=1.0,
        )
        
        expected = 0.64 * math.log1p(100) * 1.0  # 0.8^2 = 0.64
        assert abs(weight - expected) < 0.001
    
    def test_amplifies_high_similarity(self):
        formula = QuadraticFormula()
        baseline = BaselineFormula()
        
        # При similarity 0.9 vs 0.5
        high_quad = formula.calculate_weight(0.9, 100, 1.0)
        low_quad = formula.calculate_weight(0.5, 100, 1.0)
        
        high_base = baseline.calculate_weight(0.9, 100, 1.0)
        low_base = baseline.calculate_weight(0.5, 100, 1.0)
        
        # Квадратичная формула должна сильнее различать
        quad_ratio = high_quad / low_quad
        base_ratio = high_base / low_base
        
        assert quad_ratio > base_ratio
    
    def test_name(self):
        assert QuadraticFormula().get_name() == "quadratic"


class TestExponentialFormula:
    """Тесты F4: Exponential."""
    
    def test_basic_calculation(self):
        formula = ExponentialFormula(center=0.5)
        
        weight = formula.calculate_weight(
            similarity=0.8,
            vacancy_count=100,
            grade_coeff=1.0,
        )
        
        expected = math.exp(0.3) * math.log1p(100) * 1.0
        assert abs(weight - expected) < 0.001
    
    def test_center_gives_exp_one(self):
        formula = ExponentialFormula(center=0.5)
        
        weight = formula.calculate_weight(
            similarity=0.5,
            vacancy_count=100,
            grade_coeff=1.0,
        )
        
        # exp(0) = 1
        expected = 1.0 * math.log1p(100) * 1.0
        assert abs(weight - expected) < 0.001
    
    def test_name(self):
        assert ExponentialFormula().get_name() == "exponential"


class TestTFIDFFormula:
    """Тесты F5: TF-IDF."""
    
    def test_basic_calculation(self):
        formula = TFIDFFormula(total_vacancies=10000)
        
        weight = formula.calculate_weight(
            similarity=0.8,
            vacancy_count=100,
            grade_coeff=1.0,
        )
        
        idf = math.log(10000 / 100)  # log(100) = 4.6
        expected = 0.8 * idf * 1.0
        assert abs(weight - expected) < 0.001
    
    def test_rare_skills_weighted_higher(self):
        formula = TFIDFFormula(total_vacancies=10000)
        
        rare = formula.calculate_weight(0.8, 10, 1.0)
        common = formula.calculate_weight(0.8, 1000, 1.0)
        
        assert rare > common
    
    def test_zero_count(self):
        formula = TFIDFFormula()
        weight = formula.calculate_weight(0.8, 0, 1.0)
        assert weight == 0.0
    
    def test_name(self):
        assert TFIDFFormula().get_name() == "tfidf"


class TestMatrixFormula:
    """Тесты F6: Matrix."""
    
    def test_no_context_equals_baseline(self):
        """Без контекста матричная формула ведёт себя как baseline."""
        matrix = MatrixFormula()
        baseline = BaselineFormula()
        
        m_weight = matrix.calculate_weight(0.8, 100, 1.0)
        b_weight = baseline.calculate_weight(0.8, 100, 1.0)
        
        # Correlation boost = 1.0 без контекста
        assert abs(m_weight - b_weight) < 0.001
    
    def test_correlated_skills_boosted(self):
        """Связанные навыки получают boost."""
        # Симулируем три похожих навыка (близкие эмбеддинги)
        emb_python = [0.9, 0.1, 0.0]
        emb_django = [0.85, 0.15, 0.0]  # Похож на Python
        emb_excel = [0.0, 0.1, 0.9]  # Не похож
        
        skill_embeddings = {
            "Python": emb_python,
            "Django": emb_django,
            "Excel": emb_excel,
        }
        
        formula = MatrixFormula(
            skill_embeddings=skill_embeddings,
            current_skill="Python",
            boost_scale=0.5,
        )
        
        weight_python = formula.calculate_weight(0.8, 100, 1.0)
        
        # Сменим контекст на Excel
        formula.set_context(skill_embeddings, "Excel")
        weight_excel = formula.calculate_weight(0.8, 100, 1.0)
        
        # Python должен получить больший boost (он ближе к Django)
        assert weight_python > weight_excel
    
    def test_name(self):
        assert MatrixFormula().get_name() == "matrix"


class TestFormulaRegistry:
    """Тесты FormulaRegistry."""
    
    def test_list_all_formulas(self):
        formulas = FormulaRegistry.list_formulas()
        
        assert "baseline" in formulas
        assert "linear" in formulas
        assert "quadratic" in formulas
        assert "exponential" in formulas
        assert "tfidf" in formulas
        assert "matrix" in formulas
        assert len(formulas) == 6
    
    def test_get_each_formula(self):
        for name in FormulaRegistry.list_formulas():
            formula = FormulaRegistry.get_formula(name)
            assert formula.get_name() == name
    
    def test_unknown_formula_raises(self):
        with pytest.raises(ValueError, match="Unknown formula"):
            FormulaRegistry.get_formula("unknown")
    
    def test_get_all_formulas(self):
        formulas = FormulaRegistry.get_all_formulas()
        assert len(formulas) == 6
        
        names = [f.get_name() for f in formulas]
        assert "baseline" in names
    
    def test_formula_with_params(self):
        """Можно передать параметры в конструктор."""
        formula = FormulaRegistry.get_formula("linear", max_count=500)
        
        # С max_count=500, count=500 даёт normalized=1.0
        weight = formula.calculate_weight(1.0, 500, 1.0)
        assert abs(weight - 1.0) < 0.001
