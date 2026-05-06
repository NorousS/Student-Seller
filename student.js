const tabs = document.querySelectorAll('.student-tab');
const views = document.querySelectorAll('.student-view');
const skillsForm = document.querySelector('#skills-form');
const disciplineNameInput = document.querySelector('#discipline-name');
const disciplineScoreInput = document.querySelector('#discipline-score');
const skillsList = document.querySelector('#skills-list');
const scoreValue = document.querySelector('#candidate-score');
const scoreBadge = document.querySelector('#score-badge');
const scoreDescription = document.querySelector('#score-description');
const averageScore = document.querySelector('#average-score');
const skillsCount = document.querySelector('#skills-count');
const skillsHint = document.querySelector('#skills-hint');
const chartCanvas = document.querySelector('#skills-chart');
const scoreBreakdown = document.querySelector('#score-breakdown');

const marketBaseline = {
  'JavaScript': 74,
  'React': 71,
  'UI/UX': 68,
  'Алгоритмы': 72,
  'Командная работа': 79,
};

const skills = [
  { name: 'Объектно ориентированное программирование', score: 97 },
  { name: 'JavaScript', score: 92 },
  { name: 'React', score: 88 },
];

function showTab(tabName) {
  tabs.forEach((tab) => {
    const isActive = tab.dataset.tab === tabName;
    tab.classList.toggle('is-active', isActive);
    tab.setAttribute('aria-selected', String(isActive));
  });

  views.forEach((view) => {
    view.classList.toggle('is-active', view.dataset.view === tabName);
  });
}

function clampScore(value) {
  return Math.min(100, Math.max(51, value));
}

function buildComparisonData() {
  const namedSkills = Object.keys(marketBaseline).map((name) => {
    const match = skills.find((skill) => skill.name.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(skill.name.toLowerCase()));
    const studentScore = match ? match.score : 60;

    return {
      label: name,
      student: studentScore,
      market: marketBaseline[name],
    };
  });

  return namedSkills;
}

function renderSkills() {
  skillsList.innerHTML = '';

  skills.forEach((skill) => {
    const row = document.createElement('div');
    row.className = 'skills-row';
    row.innerHTML = `
      <strong>${skill.name}</strong>
      <span>${skill.score}</span>
    `;
    skillsList.append(row);
  });
}

function updateScore() {
  if (!skills.length) {
    scoreValue.textContent = '0';
    scoreBadge.textContent = 'Нет данных';
    scoreDescription.textContent = 'Добавьте навыки и оценки, чтобы получить прогноз по профилю студента.';
    averageScore.textContent = '0';
    skillsCount.textContent = '0';
    scoreBreakdown.innerHTML = '';
    return;
  }

  const average = Math.round(skills.reduce((sum, skill) => sum + skill.score, 0) / skills.length);
  const consistencyBonus = Math.min(6, Math.floor(skills.length / 2));
  const finalScore = Math.min(100, average + consistencyBonus);
  let level = 'Требует усиления';

  if (finalScore >= 90) {
    level = 'Сильный профиль';
  } else if (finalScore >= 80) {
    level = 'Хороший уровень';
  } else if (finalScore >= 70) {
    level = 'Уверенный старт';
  }

  scoreValue.textContent = String(finalScore);
  scoreBadge.textContent = level;
  averageScore.textContent = String(average);
  skillsCount.textContent = String(skills.length);
  scoreDescription.textContent = `Итоговая оценка строится из среднего балла по дисциплинам и небольшого бонуса за ширину профиля. Сейчас студент выглядит как кандидат на ${finalScore} из 100.`;

  const breakdown = buildComparisonData()
    .map((item) => {
      const delta = item.student - item.market;
      const deltaClass = delta >= 0 ? 'score-breakdown__delta--up' : 'score-breakdown__delta--down';
      const deltaText = `${delta >= 0 ? '+' : ''}${delta}`;

      return `
        <div class="score-breakdown__item">
          <strong>${item.label}</strong>
          <span>${item.student} vs ${item.market}</span>
          <span class="${deltaClass}">${deltaText}</span>
        </div>
      `;
    })
    .join('');

  scoreBreakdown.innerHTML = breakdown;
}

function drawChart() {
  if (!chartCanvas) {
    return;
  }

  const context = chartCanvas.getContext('2d');
  const data = buildComparisonData();
  const width = chartCanvas.width;
  const height = chartCanvas.height;
  const paddingLeft = 34;
  const paddingTop = 34;
  const labelWidth = 118;
  const valueWidth = 52;
  const chartWidth = width - paddingLeft - labelWidth - valueWidth - 18;
  const barHeight = 14;
  const groupGap = 52;

  context.clearRect(0, 0, width, height);
  context.fillStyle = '#12162a';
  context.font = '14px Rubik';

  for (let step = 0; step <= 100; step += 25) {
    const x = paddingLeft + labelWidth + (chartWidth * step / 100);
    context.strokeStyle = 'rgba(18, 22, 42, 0.12)';
    context.beginPath();
    context.moveTo(x, paddingTop - 10);
    context.lineTo(x, height - 26);
    context.stroke();

    context.fillStyle = '#7d8294';
    context.fillText(String(step), x - 6, 20);
  }

  data.forEach((item, index) => {
    const y = paddingTop + index * groupGap;
    const barStartX = paddingLeft + labelWidth;
    const studentWidth = chartWidth * (item.student / 100);
    const marketWidth = chartWidth * (item.market / 100);

    context.fillStyle = '#12162a';
    context.fillText(item.label, paddingLeft, y + 10);

    context.fillStyle = '#dce0f6';
    context.fillRect(barStartX, y, chartWidth, barHeight);
    context.fillRect(barStartX, y + 18, chartWidth, barHeight);

    context.fillStyle = '#2827f0';
    context.fillRect(barStartX, y, studentWidth, barHeight);

    context.fillStyle = '#0f1220';
    context.fillRect(barStartX, y + 18, marketWidth, barHeight);

    context.fillStyle = '#2827f0';
    context.fillText(`${item.student}`, barStartX + chartWidth + 12, y + 12);

    context.fillStyle = '#0f1220';
    context.fillText(`${item.market}`, barStartX + chartWidth + 12, y + 30);
  });
}

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    showTab(tab.dataset.tab);
  });
});

skillsForm.addEventListener('submit', (event) => {
  event.preventDefault();

  const name = disciplineNameInput.value.trim();
  const score = Number(disciplineScoreInput.value);

  if (!name) {
    skillsHint.textContent = 'Введите название дисциплины.';
    return;
  }

  if (!Number.isFinite(score) || score < 51 || score > 100) {
    skillsHint.textContent = 'Оценка должна быть в диапазоне от 51 до 100.';
    return;
  }

  skills.push({
    name,
    score: clampScore(score),
  });

  disciplineNameInput.value = '';
  disciplineScoreInput.value = '100';
  skillsHint.textContent = 'Навык добавлен. Оценка и график уже обновились.';

  renderSkills();
  updateScore();
  drawChart();
});

renderSkills();
updateScore();
drawChart();
showTab('profile');
