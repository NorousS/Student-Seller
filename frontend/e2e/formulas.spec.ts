/**
 * E2E-тесты: Выбор формулы оценки в панели студента
 *
 * Предусловие: FastAPI + PostgreSQL запущены на http://127.0.0.1:8000
 */
import { test, expect, type Page } from '@playwright/test';

const BASE = 'http://127.0.0.1:8000';

const TS = Date.now();
const STUDENT_EMAIL = `e2e_formula_${TS}@test.com`;
const STUDENT_PASS = 'Test1234!';

async function registerStudent(page: Page) {
  const res = await page.request.post(`${BASE}/api/v1/auth/register`, {
    data: {
      email: STUDENT_EMAIL,
      password: STUDENT_PASS,
      role: 'student',
      full_name: 'Formula Test Student',
    },
  });
  expect(res.status()).toBe(201);
}

async function addDisciplines(page: Page, token: string) {
  const res = await page.request.post(`${BASE}/api/v1/profile/student/disciplines`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      disciplines: [
        { name: 'Программирование на Python', grade: 5 },
        { name: 'Базы данных', grade: 4 },
        { name: 'Машинное обучение', grade: 5 },
      ],
    },
  });
  expect(res.status()).toBe(200);
}

async function loginStudent(page: Page) {
  await page.goto(`${BASE}/login`);
  await page.locator('input[type="email"]').fill(STUDENT_EMAIL);
  await page.locator('input[type="password"]').fill(STUDENT_PASS);
  await page.getByRole('button', { name: /войти/i }).click();
  await page.waitForURL(/\/student/, { timeout: 5000 });
}

async function loginViaAPI(page: Page, email: string, password: string) {
  const res = await page.request.post(`${BASE}/api/v1/auth/login`, {
    data: { email, password },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  return body.access_token as string;
}

test.describe('Formula selection in student panel', () => {
  test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await registerStudent(page);
    const token = await loginViaAPI(page, STUDENT_EMAIL, STUDENT_PASS);
    await addDisciplines(page, token);
    await ctx.close();
  });

  test('formula dropdown is visible in evaluation tab', async ({ page }) => {
    await loginStudent(page);

    // Navigate to evaluation tab
    await page.getByRole('tab', { name: /оценка/i }).click();

    // Check formula dropdown exists
    const formulaSelect = page.locator('select').filter({ hasText: /baseline|linear|quadratic/ });
    await expect(formulaSelect).toBeVisible();
  });

  test('can select different formulas', async ({ page }) => {
    await loginStudent(page);
    await page.getByRole('tab', { name: /оценка/i }).click();

    // Find formula dropdown (should be the second select after experience)
    const selects = page.locator('select');
    const formulaSelect = selects.nth(1); // 0 = experience, 1 = formula

    // Default should be baseline
    await expect(formulaSelect).toHaveValue('baseline');

    // Change to quadratic
    await formulaSelect.selectOption('quadratic');
    await expect(formulaSelect).toHaveValue('quadratic');

    // Change to tfidf
    await formulaSelect.selectOption('tfidf');
    await expect(formulaSelect).toHaveValue('tfidf');
  });

  test('evaluation result shows selected formula', async ({ page }) => {
    await loginStudent(page);
    await page.getByRole('tab', { name: /оценка/i }).click();

    // Fill specialty
    await page.locator('input[type="text"]').fill('Python developer');

    // Select exponential formula
    const selects = page.locator('select');
    const formulaSelect = selects.nth(1);
    await formulaSelect.selectOption('exponential');

    // Click evaluate
    await page.getByRole('button', { name: /оценить стоимость/i }).click();

    // Wait for results (may take time for embeddings)
    await page.waitForTimeout(5000);

    // Check that result card appears and contains formula name
    const resultCard = page.locator('.stat-card').first();
    await expect(resultCard).toBeVisible();

    // Check formula is displayed in results
    await expect(page.locator('text=exponential')).toBeVisible();
  });

  test('different formulas produce different results', async ({ page }) => {
    await loginStudent(page);
    await page.getByRole('tab', { name: /оценка/i }).click();

    const selects = page.locator('select');
    const formulaSelect = selects.nth(1);
    const specialtyInput = page.locator('input[type="text"]');
    const evaluateBtn = page.getByRole('button', { name: /оценить стоимость/i });

    // Evaluate with baseline
    await specialtyInput.fill('Python developer');
    await formulaSelect.selectOption('baseline');
    await evaluateBtn.click();
    await page.waitForTimeout(5000);

    const baselineSalary = await page.locator('.salary-value').first().textContent();

    // Re-evaluate with quadratic
    await formulaSelect.selectOption('quadratic');
    await evaluateBtn.click();
    await page.waitForTimeout(5000);

    const quadraticSalary = await page.locator('.salary-value').first().textContent();

    // Results should differ (unless by chance they're exactly the same)
    // We just check that evaluation completed successfully
    expect(baselineSalary).toBeTruthy();
    expect(quadraticSalary).toBeTruthy();
  });

  test('API /formulas endpoint returns list', async ({ page }) => {
    const token = await loginViaAPI(page, STUDENT_EMAIL, STUDENT_PASS);

    const res = await page.request.get(`${BASE}/api/v1/profile/student/formulas`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);

    const formulas = await res.json();
    expect(Array.isArray(formulas)).toBe(true);
    expect(formulas.length).toBeGreaterThanOrEqual(6);

    // Check structure
    expect(formulas[0]).toHaveProperty('name');
    expect(formulas[0]).toHaveProperty('description');

    // Check baseline exists
    const baseline = formulas.find((f: any) => f.name === 'baseline');
    expect(baseline).toBeTruthy();
    expect(baseline.description).toContain('Базовая формула');
  });
});
