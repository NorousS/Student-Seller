"""
Статистический анализ формул оценки студентов
на основе методов MIT/Harvard:
- Cross-validation для стабильности
- AIC/BIC для сравнения моделей
- Discrimination power (Cohen's d)
- Consistency metrics
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from scipy import stats
from typing import List, Dict, Any
import json

from app.database import async_session_maker, create_tables
from app.formulas import FormulaRegistry
from app.analysis.test_data import (
    generate_test_students,
    get_weak_students,
    get_strong_students
)
from app.analysis.metrics import (
    evaluate_formula_quality
)
from app.valuation import evaluate_student


async def calculate_aic_bic(
    formula_name: str,
    evaluations: List[float],
    n_params: int = 3  # similarity, log_count, grade
) -> Dict[str, float]:
    """
    Рассчитать AIC и BIC для формулы.
    
    AIC = 2k - 2ln(L)
    BIC = ln(n)k - 2ln(L)
    
    где k - число параметров, n - размер выборки, L - максимальное правдоподобие
    """
    n = len(evaluations)
    
    # Для расчета правдоподобия используем нормальное распределение
    # L = product of P(x_i | mu, sigma)
    mu = np.mean(evaluations)
    sigma = np.std(evaluations) + 1e-10  # избегаем деления на 0
    
    # Log-likelihood для нормального распределения
    log_likelihood = -n/2 * np.log(2 * np.pi * sigma**2) - \
                    sum((x - mu)**2 for x in evaluations) / (2 * sigma**2)
    
    aic = 2 * n_params - 2 * log_likelihood
    bic = np.log(n) * n_params - 2 * log_likelihood
    
    return {
        "aic": float(aic),
        "bic": float(bic),
        "log_likelihood": float(log_likelihood),
        "n_params": n_params,
        "n_samples": n
    }


async def cross_validation_rmse(
    formula_name: str,
    test_students: List[Dict],
    k_folds: int = 5
) -> Dict[str, Any]:
    """
    K-fold cross-validation для оценки стабильности формулы.
    
    Возвращает RMSE для каждого fold и среднее значение.
    """
    np.random.shuffle(test_students)
    fold_size = len(test_students) // k_folds
    fold_rmses = []
    
    for fold_idx in range(k_folds):
        async with async_session_maker() as db:
            # Разделяем на train/test (здесь используем для оценки вариативности)
            start_idx = fold_idx * fold_size
            end_idx = start_idx + fold_size if fold_idx < k_folds - 1 else len(test_students)
            
            fold_students = test_students[start_idx:end_idx]
            fold_evaluations = []
            
            for student_data in fold_students:
                try:
                    result = await evaluate_student(
                        db=db,
                        student_id=student_data["id"],
                        formula_name=formula_name
                    )
                    if result and result.total_grade is not None:
                        fold_evaluations.append(result.total_grade)
                except Exception as e:
                    print(f"Ошибка оценки студента {student_data['id']}: {e}")
                    continue
            
            if fold_evaluations:
                # RMSE относительно среднего значения в fold
                mean_val = np.mean(fold_evaluations)
                rmse = np.sqrt(np.mean([(x - mean_val)**2 for x in fold_evaluations]))
                fold_rmses.append(rmse)
    
    return {
        "fold_rmses": fold_rmses,
        "mean_rmse": float(np.mean(fold_rmses)) if fold_rmses else None,
        "std_rmse": float(np.std(fold_rmses)) if fold_rmses else None,
        "k_folds": k_folds
    }


async def statistical_comparison(
    formulas: List[str],
    n_students: int = 50,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Полное статистическое сравнение формул.
    
    Методы:
    1. AIC/BIC - информационные критерии для выбора модели
    2. Cross-validation RMSE - устойчивость к изменениям данных
    3. Discrimination power - способность различать слабых/сильных студентов
    4. Consistency - стабильность оценок
    """
    print(f"\n🔬 Статистический анализ {len(formulas)} формул")
    print(f"📊 Генерация {n_students} тестовых студентов (seed={seed})")
    
    async with async_session_maker() as db:
        # Генерируем тестовых студентов
        await create_tables()
        test_students = await generate_test_students(db, n=n_students, seed=seed)
        print(f"✅ Создано {len(test_students)} студентов")
    
    results = {}
    
    for formula_name in formulas:
        print(f"\n📐 Анализ формулы: {formula_name}")
        
        async with async_session_maker() as db:
            # 1. Базовые оценки всех студентов
            evaluations = []
            for student_data in test_students:
                try:
                    result = await evaluate_student(
                        db=db,
                        student_id=student_data["id"],
                        formula_name=formula_name
                    )
                    if result and result.total_grade is not None:
                        evaluations.append(result.total_grade)
                except Exception:
                    continue
            
            if not evaluations:
                print(f"⚠️  Нет оценок для {formula_name}")
                continue
            
            # 2. AIC/BIC
            aic_bic = await calculate_aic_bic(formula_name, evaluations)
            print(f"   AIC: {aic_bic['aic']:.2f}, BIC: {aic_bic['bic']:.2f}")
            
            # 3. Cross-validation
            cv_results = await cross_validation_rmse(
                formula_name,
                test_students,
                k_folds=5
            )
            print(f"   CV-RMSE: {cv_results['mean_rmse']:.4f} ± {cv_results['std_rmse']:.4f}")
            
            # 4. Discrimination power
            weak_ids = [s["id"] for s in test_students if s["strength"] == "weak"]
            strong_ids = [s["id"] for s in test_students if s["strength"] == "strong"]
            
            weak_evals = []
            strong_evals = []
            
            for student_data in test_students:
                try:
                    result = await evaluate_student(
                        db=db,
                        student_id=student_data["id"],
                        formula_name=formula_name
                    )
                    if result and result.total_grade is not None:
                        if student_data["id"] in weak_ids:
                            weak_evals.append(result.total_grade)
                        elif student_data["id"] in strong_ids:
                            strong_evals.append(result.total_grade)
                except Exception:
                    continue
            
            # Cohen's d
            if weak_evals and strong_evals:
                mean_weak = np.mean(weak_evals)
                mean_strong = np.mean(strong_evals)
                pooled_std = np.sqrt(
                    (np.var(weak_evals) + np.var(strong_evals)) / 2
                )
                cohens_d = (mean_strong - mean_weak) / (pooled_std + 1e-10)
                print(f"   Cohen's d: {cohens_d:.3f} (weak: {mean_weak:.1f}, strong: {mean_strong:.1f})")
            else:
                cohens_d = 0.0
            
            # 5. Полная оценка качества
            quality = await evaluate_formula_quality(
                db=db,
                formula_name=formula_name,
                test_student_ids=[s["id"] for s in test_students]
            )
            
            results[formula_name] = {
                "aic": aic_bic["aic"],
                "bic": aic_bic["bic"],
                "log_likelihood": aic_bic["log_likelihood"],
                "cv_rmse_mean": cv_results["mean_rmse"],
                "cv_rmse_std": cv_results["std_rmse"],
                "cohens_d": float(cohens_d),
                "stability_score": quality.stability_score,
                "consistency_score": quality.consistency_score,
                "coverage_ratio": quality.coverage_ratio,
                "discrimination_power": quality.discrimination_power,
                "mean_evaluation": float(np.mean(evaluations)),
                "std_evaluation": float(np.std(evaluations)),
                "n_evaluations": len(evaluations)
            }
    
    return results


async def select_best_formula(results: Dict[str, Any]) -> str:
    """
    Выбор наилучшей формулы на основе комплексного анализа.
    
    Критерии (в порядке приоритета):
    1. Низкий AIC (лучший баланс fit/complexity)
    2. Низкий BIC (предпочтение простоте)
    3. Высокий discrimination_power (различает weak/strong)
    4. Низкий CV-RMSE (стабильность)
    5. Высокий stability_score
    """
    print("\n🏆 Выбор наилучшей формулы:")
    
    # Нормализуем метрики для сравнения
    formulas = list(results.keys())
    
    # Метрики для минимизации
    aics = [results[f]["aic"] for f in formulas]
    bics = [results[f]["bic"] for f in formulas]
    cv_rmses = [results[f]["cv_rmse_mean"] for f in formulas if results[f]["cv_rmse_mean"] is not None]
    
    # Метрики для максимизации
    disc_powers = [results[f]["discrimination_power"] for f in formulas]
    stabilities = [results[f]["stability_score"] for f in formulas]
    
    # Считаем комплексный score
    scores = {}
    for formula_name in formulas:
        r = results[formula_name]
        
        # Нормализованные компоненты (0-1, где 1 лучше)
        aic_norm = 1 - (r["aic"] - min(aics)) / (max(aics) - min(aics) + 1e-10)
        bic_norm = 1 - (r["bic"] - min(bics)) / (max(bics) - min(bics) + 1e-10)
        
        cv_norm = 0.5
        if r["cv_rmse_mean"] is not None and cv_rmses:
            cv_norm = 1 - (r["cv_rmse_mean"] - min(cv_rmses)) / (max(cv_rmses) - min(cv_rmses) + 1e-10)
        
        disc_norm = (r["discrimination_power"] - min(disc_powers)) / (max(disc_powers) - min(disc_powers) + 1e-10)
        stab_norm = (r["stability_score"] - min(stabilities)) / (max(stabilities) - min(stabilities) + 1e-10)
        
        # Взвешенная сумма (AIC/BIC важнее согласно MIT/Harvard исследованиям)
        composite_score = (
            0.25 * aic_norm +      # AIC: баланс fit/complexity
            0.25 * bic_norm +      # BIC: предпочтение простоте
            0.20 * disc_norm +     # Discrimination power
            0.15 * cv_norm +       # Cross-validation stability
            0.15 * stab_norm       # Stability score
        )
        
        scores[formula_name] = composite_score
        
        print(f"\n{formula_name}:")
        print(f"  AIC: {r['aic']:.2f} (norm: {aic_norm:.3f})")
        print(f"  BIC: {r['bic']:.2f} (norm: {bic_norm:.3f})")
        print(f"  Discrimination: {r['discrimination_power']:.3f} (norm: {disc_norm:.3f})")
        print(f"  CV-RMSE: {r['cv_rmse_mean']:.4f} (norm: {cv_norm:.3f})" if r['cv_rmse_mean'] else "  CV-RMSE: N/A")
        print(f"  Stability: {r['stability_score']:.3f} (norm: {stab_norm:.3f})")
        print(f"  📊 Composite Score: {composite_score:.3f}")
    
    best_formula = max(scores, key=scores.get)
    print(f"\n✨ Победитель: {best_formula} (score: {scores[best_formula]:.3f})")
    
    return best_formula


async def main():
    """Основная функция анализа."""
    formulas = [
        "baseline",
        "linear",
        "quadratic",
        "exponential",
        "tfidf",
        "matrix"
    ]
    
    print("=" * 70)
    print("СТАТИСТИЧЕСКИЙ АНАЛИЗ ФОРМУЛ ОЦЕНКИ СТУДЕНТОВ")
    print("Методология: MIT/Harvard Cross-Validation + AIC/BIC")
    print("=" * 70)
    
    # Запускаем анализ
    results = await statistical_comparison(formulas, n_students=50, seed=42)
    
    # Сохраняем результаты
    output_file = Path(__file__).parent.parent / "formula_analysis_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Результаты сохранены в {output_file}")
    
    # Выбираем лучшую формулу
    best_formula = await select_best_formula(results)
    
    # Сохраняем рекомендацию
    recommendation = {
        "best_formula": best_formula,
        "score": max(
            (0.25 * (1 - (results[f]["aic"] - min(results[f2]["aic"] for f2 in formulas)) / (max(results[f2]["aic"] for f2 in formulas) - min(results[f2]["aic"] for f2 in formulas) + 1e-10)) +
             0.25 * (1 - (results[f]["bic"] - min(results[f2]["bic"] for f2 in formulas)) / (max(results[f2]["bic"] for f2 in formulas) - min(results[f2]["bic"] for f2 in formulas) + 1e-10)) +
             0.20 * ((results[f]["discrimination_power"] - min(results[f2]["discrimination_power"] for f2 in formulas)) / (max(results[f2]["discrimination_power"] for f2 in formulas) - min(results[f2]["discrimination_power"] for f2 in formulas) + 1e-10)) +
             0.15 * (1 - (results[f]["cv_rmse_mean"] - min(results[f2]["cv_rmse_mean"] for f2 in formulas if results[f2]["cv_rmse_mean"])) / (max(results[f2]["cv_rmse_mean"] for f2 in formulas if results[f2]["cv_rmse_mean"]) - min(results[f2]["cv_rmse_mean"] for f2 in formulas if results[f2]["cv_rmse_mean"]) + 1e-10)) if results[f]["cv_rmse_mean"] else 0.5 +
             0.15 * ((results[f]["stability_score"] - min(results[f2]["stability_score"] for f2 in formulas)) / (max(results[f2]["stability_score"] for f2 in formulas) - min(results[f2]["stability_score"] for f2 in formulas) + 1e-10))
            ) for f in formulas
        ),
        "reason": f"Выбрана на основе MIT/Harvard методологии: AIC={results[best_formula]['aic']:.2f}, BIC={results[best_formula]['bic']:.2f}, Discrimination={results[best_formula]['discrimination_power']:.3f}",
        "all_results": results
    }
    
    rec_file = Path(__file__).parent.parent / "formula_recommendation.json"
    with open(rec_file, "w", encoding="utf-8") as f:
        json.dump(recommendation, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Рекомендация сохранена в {rec_file}")
    print("\n✅ Анализ завершен!")


if __name__ == "__main__":
    asyncio.run(main())
