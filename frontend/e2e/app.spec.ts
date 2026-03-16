/**
 * E2E-тесты: Лендинг, Авторизация, Панель работодателя.
 *
 * Предусловие: FastAPI + PostgreSQL запущены на http://127.0.0.1:8000
 */
import { test, expect, type Page } from '@playwright/test';

const BASE = 'http://127.0.0.1:8000';

// Unique suffix so parallel runs don't collide
const TS = Date.now();
const EMPLOYER_EMAIL = `e2e_emp_${TS}@test.com`;
const EMPLOYER_PASS = 'Test1234!';
const STUDENT_EMAIL = `e2e_stu_${TS}@test.com`;
const STUDENT_PASS = 'Test1234!';

/* ---------- helpers ---------- */

async function registerViaAPI(
  page: Page,
  email: string,
  password: string,
  role: 'employer' | 'student',
  extra: Record<string, string> = {},
) {
  const res = await page.request.post(`${BASE}/api/v1/auth/register`, {
    data: { email, password, role, ...extra },
  });
  expect(res.status()).toBe(201);
  return res.json();
}

async function loginViaAPI(page: Page, email: string, password: string) {
  const res = await page.request.post(`${BASE}/api/v1/auth/login`, {
    data: { email, password },
  });
  expect(res.status()).toBe(200);
  const body = await res.json();
  return body.access_token as string;
}

async function loginViaUI(page: Page, email: string, password: string) {
  await page.goto(`${BASE}/login`);
  // Labels are not linked via for/id; use input[type] selectors
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: /войти/i }).click();
}

/* ============================================================
   1. Лендинг (публичная страница)
   ============================================================ */

test.describe('Landing page', () => {
  test('renders hero section and top-students cards', async ({ page }) => {
    await page.goto(`${BASE}/landing`);

    // Hero
    await expect(page.getByText('Найдите лучших выпускников')).toBeVisible();

    // Top-5 heading
    await expect(page.getByText('Топ-5 кандидатов')).toBeVisible();

    // Should show student cards OR empty-state text
    const cards = page.locator('.card');
    const empty = page.getByText('Пока нет профилей студентов');
    await expect(cards.first().or(empty)).toBeVisible();
  });

  test('CTA button redirects to /register', async ({ page }) => {
    await page.goto(`${BASE}/landing`);
    await page.getByRole('button', { name: /зарегистрироваться/i }).click();
    await expect(page).toHaveURL(/\/register/);
  });

  test('invite button on card redirects to /login', async ({ page }) => {
    await page.goto(`${BASE}/landing`);
    // Wait for cards to load
    await page.waitForTimeout(1500);
    const inviteBtn = page.getByRole('button', { name: /пригласить/i }).first();
    if (await inviteBtn.isVisible()) {
      await inviteBtn.click();
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

/* ============================================================
   2. Регистрация и вход
   ============================================================ */

test.describe('Auth flow', () => {
  test('register employer via UI', async ({ page }) => {
    await page.goto(`${BASE}/register`);

    // Select employer role first (it shows/hides fields)
    await page.locator('select').selectOption('employer');

    await page.locator('input[type="email"]').fill(EMPLOYER_EMAIL);
    await page.locator('input[type="password"]').fill(EMPLOYER_PASS);
    // Company name field is visible for employer
    await page.locator('input[name="organization"]').fill('E2E Test Corp');
    await page.getByRole('button', { name: /зарегистрироваться/i }).click();

    // Should redirect to login or employer panel
    await page.waitForURL(/\/(login|employer)/, { timeout: 5000 });
  });

  test('login as employer via UI', async ({ page }) => {
    // Ensure user exists
    await registerViaAPI(page, `e2e_login_${TS}@test.com`, EMPLOYER_PASS, 'employer', {
      company_name: 'Test Co',
    });

    await loginViaUI(page, `e2e_login_${TS}@test.com`, EMPLOYER_PASS);

    // Should end up on employer panel
    await page.waitForURL(/\/employer/, { timeout: 5000 });
    await expect(page.getByRole('tab', { name: /поиск/i })).toBeVisible();
  });

  test('login as student redirects to /student', async ({ page }) => {
    await registerViaAPI(page, STUDENT_EMAIL, STUDENT_PASS, 'student', {
      full_name: 'E2E Student',
    });

    await loginViaUI(page, STUDENT_EMAIL, STUDENT_PASS);
    await page.waitForURL(/\/student/, { timeout: 5000 });
  });
});

/* ============================================================
   3. Панель работодателя (Employer Panel)
   ============================================================ */

test.describe('Employer panel', () => {
  let employerEmail: string;

  test.beforeAll(async ({ browser }) => {
    employerEmail = `e2e_emppanel_${TS}@test.com`;
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await registerViaAPI(page, employerEmail, EMPLOYER_PASS, 'employer', {
      company_name: 'E2E Corp',
    });
    await ctx.close();
  });

  test('tabs are visible after login', async ({ page }) => {
    await loginViaUI(page, employerEmail, EMPLOYER_PASS);
    await page.waitForURL(/\/employer/, { timeout: 5000 });

    await expect(page.getByRole('tab', { name: /поиск/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /запросы/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /чат/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /профиль/i })).toBeVisible();
  });

  test('profile tab shows company form', async ({ page }) => {
    await loginViaUI(page, employerEmail, EMPLOYER_PASS);
    await page.waitForURL(/\/employer/, { timeout: 5000 });

    // Click profile tab
    await page.getByText('Профиль', { exact: false }).click();
    await expect(page.getByText('Профиль компании')).toBeVisible();
    await expect(page.getByRole('button', { name: /сохранить/i })).toBeVisible();
  });

  test('search tab allows searching students', async ({ page }) => {
    await loginViaUI(page, employerEmail, EMPLOYER_PASS);
    await page.waitForURL(/\/employer/, { timeout: 5000 });

    // Search tab should be active by default
    const searchInput = page.getByPlaceholder(/python/i);
    await expect(searchInput).toBeVisible();

    await searchInput.fill('Python разработчик');
    await page.getByRole('button', { name: /найти/i }).click();

    // Wait for results (might take a few seconds due to embedding)
    await page.waitForTimeout(3000);

    // Results section should update
    await expect(page.getByText('Результаты')).toBeVisible();
  });

  test('requests tab shows empty state', async ({ page }) => {
    await loginViaUI(page, employerEmail, EMPLOYER_PASS);
    await page.waitForURL(/\/employer/, { timeout: 5000 });

    await page.getByText('Запросы', { exact: false }).click();
    await expect(page.getByText('Нет запросов')).toBeVisible();
  });
});

/* ============================================================
   4. SPA-роутинг
   ============================================================ */

test.describe('SPA routing', () => {
  test('unknown routes redirect unauthenticated to /landing', async ({ page }) => {
    await page.goto(`${BASE}/`);
    await page.waitForURL(/\/(landing|login)/, { timeout: 5000 });
  });

  test('/employer redirects unauthenticated to /login', async ({ page }) => {
    await page.goto(`${BASE}/employer`);
    await page.waitForURL(/\/login/, { timeout: 5000 });
  });

  test('/student redirects unauthenticated to /login', async ({ page }) => {
    await page.goto(`${BASE}/student`);
    await page.waitForURL(/\/login/, { timeout: 5000 });
  });
});

/* ============================================================
   5. API smoke tests via page.request (paywall + contacts)
   ============================================================ */

test.describe('API: Invite & Paywall flow', () => {
  test('non-partner employer gets paywall_required on invite', async ({ page }) => {
    const email = `e2e_paywall_${TS}@test.com`;
    await registerViaAPI(page, email, EMPLOYER_PASS, 'employer', { company_name: 'Paywall Co' });
    const token = await loginViaAPI(page, email, EMPLOYER_PASS);

    // Get a real student ID from top-students
    const topRes = await page.request.get(`${BASE}/api/v1/landing/top-students`);
    const students = await topRes.json();
    if (students.length === 0) {
      test.skip();
      return;
    }
    const studentId = students[0].student_id;

    // Attempt invite — should get paywall
    const inviteRes = await page.request.post(`${BASE}/api/v1/landing/invite/${studentId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(inviteRes.status()).toBe(200);
    const body = await inviteRes.json();
    expect(body.status).toBe('paywall_required');
    expect(body.reason).toBe('non_partner');
  });

  test('paywall-options returns options for employer', async ({ page }) => {
    const email = `e2e_pwall_opts_${TS}@test.com`;
    await registerViaAPI(page, email, EMPLOYER_PASS, 'employer', { company_name: 'Opts Co' });
    const token = await loginViaAPI(page, email, EMPLOYER_PASS);

    const res = await page.request.get(`${BASE}/api/v1/landing/paywall-options`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status()).toBe(200);
    const options = await res.json();
    expect(options.length).toBeGreaterThanOrEqual(2);
    expect(options[0]).toHaveProperty('id');
    expect(options[0]).toHaveProperty('title');
  });

  test('contacts are blocked without accepted invite', async ({ page }) => {
    const email = `e2e_contacts_${TS}@test.com`;
    await registerViaAPI(page, email, EMPLOYER_PASS, 'employer', { company_name: 'Blocked Co' });
    const token = await loginViaAPI(page, email, EMPLOYER_PASS);

    const res = await page.request.get(`${BASE}/api/v1/landing/student/1/contacts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    // Should be 403 (no accepted invite)
    expect(res.status()).toBe(403);
  });
});

/* ============================================================
   6. API: Partnership management (admin)
   ============================================================ */

test.describe('API: Partnership admin', () => {
  test('non-admin cannot change partnership status', async ({ page }) => {
    const email = `e2e_nonadmin_${TS}@test.com`;
    await registerViaAPI(page, email, EMPLOYER_PASS, 'employer', { company_name: 'NonAdmin Co' });
    const token = await loginViaAPI(page, email, EMPLOYER_PASS);

    const res = await page.request.patch(`${BASE}/api/v1/admin/partnership/employer/999`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { partnership_status: 'partner' },
    });
    expect(res.status()).toBe(403);
  });
});
