"""
SkillClusterer — группировка навыков hh.ru в категории.

Кластеризует навыки найденные в вакансиях по семантическим категориям:
- Backend: Python, Java, Go, SQL, PostgreSQL...
- Frontend: JavaScript, React, Vue, CSS...
- DevOps: Docker, Kubernetes, CI/CD, Linux...
- Data: Machine Learning, Analytics, Pandas...
- Soft Skills: Communication, Teamwork, English...
- Tools: Git, Jira, VS Code...
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from app.embeddings import embedding_service


# Якорные навыки для именования категорий
SKILL_CATEGORY_ANCHORS = {
    "backend": [
        "Python разработка",
        "Java backend",
        "Go программирование",
        "REST API",
        "PostgreSQL",
        "Микросервисы",
    ],
    "frontend": [
        "JavaScript",
        "React",
        "Vue.js",
        "TypeScript",
        "HTML CSS",
        "Адаптивная вёрстка",
    ],
    "devops": [
        "Docker контейнеризация",
        "Kubernetes",
        "CI/CD пайплайны",
        "Linux администрирование",
        "AWS облачные сервисы",
        "Terraform",
    ],
    "data": [
        "Machine Learning",
        "Data Science",
        "Pandas анализ данных",
        "Deep Learning нейросети",
        "SQL аналитика",
        "Визуализация данных",
    ],
    "soft_skills": [
        "Командная работа",
        "Коммуникация",
        "Английский язык",
        "Тайм-менеджмент",
        "Презентации",
        "Лидерство",
    ],
    "tools": [
        "Git версионирование",
        "Jira управление проектами",
        "Confluence документация",
        "VS Code IDE",
        "Postman тестирование API",
        "Figma дизайн",
    ],
    "mobile": [
        "Android разработка",
        "iOS Swift",
        "React Native",
        "Flutter",
        "Kotlin",
        "Mobile UI",
    ],
    "qa": [
        "Автоматизация тестирования",
        "Selenium",
        "Unit тесты",
        "QA методологии",
        "Pytest",
        "Тест-дизайн",
    ],
}


@dataclass
class SkillCluster:
    """Кластер навыков."""
    
    category: str
    skills: list[str]
    confidence: float  # Уверенность в категории (0..1)
    centroid: Optional[list[float]] = None


@dataclass
class SkillClusterResult:
    """Результат кластеризации навыков."""
    
    clusters: list[SkillCluster]
    uncategorized: list[str]  # Навыки не попавшие ни в одну категорию


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Вычислить косинусное сходство двух векторов."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot / (norm_a * norm_b))


class SkillClusterer:
    """
    Кластеризует навыки hh.ru по семантическим категориям.
    
    Использует предопределённые категории-якоря для именования кластеров.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.5,
        min_cluster_size: int = 2,
    ):
        """
        Args:
            similarity_threshold: Минимальное сходство для отнесения к категории
            min_cluster_size: Минимальный размер кластера
        """
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self._anchor_embeddings: dict[str, list[float]] = {}
    
    async def _ensure_anchor_embeddings(self) -> None:
        """Инициализировать эмбеддинги якорных категорий."""
        if self._anchor_embeddings:
            return
        
        for category, anchors in SKILL_CATEGORY_ANCHORS.items():
            # Средний эмбеддинг якорных навыков категории
            embeddings = await embedding_service.get_embeddings_batch(anchors)
            
            if embeddings:
                # Вычисляем центроид категории
                embeddings_arr = np.array(embeddings)
                centroid = np.mean(embeddings_arr, axis=0).tolist()
                self._anchor_embeddings[category] = centroid
    
    def _find_best_category(
        self,
        skill_embedding: list[float],
    ) -> tuple[str, float]:
        """
        Найти наиболее подходящую категорию для навыка.
        
        Returns:
            (category_name, confidence) или ("uncategorized", 0.0)
        """
        best_category = "uncategorized"
        best_similarity = 0.0
        
        for category, centroid in self._anchor_embeddings.items():
            similarity = cosine_similarity(skill_embedding, centroid)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_category = category
        
        if best_similarity < self.similarity_threshold:
            return ("uncategorized", 0.0)
        
        return (best_category, best_similarity)
    
    async def cluster(
        self,
        skills: list[str],
        skill_embeddings: Optional[dict[str, list[float]]] = None,
    ) -> SkillClusterResult:
        """
        Кластеризовать навыки по категориям.
        
        Args:
            skills: Список названий навыков
            skill_embeddings: Готовые эмбеддинги (опционально)
            
        Returns:
            SkillClusterResult с кластерами и некатегоризированными навыками
        """
        if not skills:
            return SkillClusterResult(clusters=[], uncategorized=[])
        
        await self._ensure_anchor_embeddings()
        
        # Получаем эмбеддинги навыков
        if skill_embeddings is None:
            embeddings = await embedding_service.get_embeddings_batch(skills)
            skill_embeddings = dict(zip(skills, embeddings))
        
        # Группируем по категориям
        category_skills: dict[str, list[tuple[str, float]]] = {}
        uncategorized = []
        
        for skill in skills:
            embedding = skill_embeddings.get(skill)
            
            if embedding is None:
                uncategorized.append(skill)
                continue
            
            category, confidence = self._find_best_category(embedding)
            
            if category == "uncategorized":
                uncategorized.append(skill)
            else:
                if category not in category_skills:
                    category_skills[category] = []
                category_skills[category].append((skill, confidence))
        
        # Формируем результат
        clusters = []
        
        for category, skill_confidences in category_skills.items():
            skills_in_cluster = [s for s, _ in skill_confidences]
            confidences = [c for _, c in skill_confidences]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Вычисляем центроид кластера
            cluster_embeddings = [
                skill_embeddings[s] for s in skills_in_cluster
                if s in skill_embeddings
            ]
            
            centroid = None
            if cluster_embeddings:
                centroid = np.mean(np.array(cluster_embeddings), axis=0).tolist()
            
            clusters.append(SkillCluster(
                category=category,
                skills=skills_in_cluster,
                confidence=avg_confidence,
                centroid=centroid,
            ))
        
        # Сортируем по количеству навыков
        clusters.sort(key=lambda c: len(c.skills), reverse=True)
        
        return SkillClusterResult(clusters=clusters, uncategorized=uncategorized)
    
    async def cluster_with_agglomerative(
        self,
        skills: list[str],
        n_clusters: Optional[int] = None,
    ) -> SkillClusterResult:
        """
        Альтернативная кластеризация через AgglomerativeClustering.
        
        Автоматически определяет количество кластеров если не задано.
        
        Args:
            skills: Список навыков
            n_clusters: Количество кластеров (None = авто)
            
        Returns:
            SkillClusterResult
        """
        if len(skills) < 2:
            return SkillClusterResult(
                clusters=[SkillCluster(
                    category="single",
                    skills=skills,
                    confidence=1.0,
                )] if skills else [],
                uncategorized=[],
            )
        
        await self._ensure_anchor_embeddings()
        
        # Получаем эмбеддинги
        embeddings = await embedding_service.get_embeddings_batch(skills)
        skill_embeddings = dict(zip(skills, embeddings))
        
        embeddings_matrix = np.array(embeddings)
        
        # Определяем количество кластеров
        if n_clusters is None:
            n_clusters = min(len(SKILL_CATEGORY_ANCHORS), len(skills) // 2 + 1)
            n_clusters = max(2, n_clusters)
        
        # Кластеризация
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            metric="cosine",
            linkage="average",
        )
        
        labels = clustering.fit_predict(embeddings_matrix)
        
        # Группируем навыки по кластерам
        cluster_skills: dict[int, list[str]] = {}
        
        for skill, label in zip(skills, labels):
            if label not in cluster_skills:
                cluster_skills[label] = []
            cluster_skills[label].append(skill)
        
        # Именуем кластеры через якорные категории
        clusters = []
        
        for label, skills_in_cluster in cluster_skills.items():
            # Центроид кластера
            cluster_embeddings = [
                skill_embeddings[s] for s in skills_in_cluster
            ]
            centroid = np.mean(np.array(cluster_embeddings), axis=0).tolist()
            
            # Находим ближайшую категорию
            category, confidence = self._find_best_category(centroid)
            
            clusters.append(SkillCluster(
                category=category if category != "uncategorized" else f"cluster_{label}",
                skills=skills_in_cluster,
                confidence=confidence,
                centroid=centroid,
            ))
        
        clusters.sort(key=lambda c: len(c.skills), reverse=True)
        
        return SkillClusterResult(clusters=clusters, uncategorized=[])
