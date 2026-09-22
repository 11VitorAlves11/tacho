// Creates synthetic examples on a FRESH disposable instance, then captures the real UI.
// See docs/screenshots.md. Never run against an instance containing household data.
const { mkdir } = require('node:fs/promises');
const path = require('node:path');
const { chromium, expect } = require(process.env.PLAYWRIGHT_MODULE || '@playwright/test');
const baseURL = process.env.SCREENSHOT_BASE_URL || 'http://localhost:18080';
const output = path.resolve(__dirname, '../docs/images');

(async () => {
  await mkdir(output, { recursive: true });
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 }, locale: 'pt-PT', timezoneId: 'Europe/Lisbon', colorScheme: 'light' });
    const api = context.request;
    async function request(method, url, data) {
      const response = await api[method](url, { data });
      if (!response.ok()) throw new Error(`${method} ${url}: ${response.status()} ${await response.text()}`);
      return response.status() === 204 ? null : response.json();
    }
    const status = await request('get', '/setup/status');
    if (!status.needs_setup) throw new Error('Refusing to seed an existing installation. Use a fresh disposable database.');
    await request('post', '/setup', { name: 'Alex', email: 'demo@example.com', password: 'TachoDemo2026!' });
    const login = await api.post('/auth/cookie/login', { form: { username: 'demo@example.com', password: 'TachoDemo2026!' } });
    if (!login.ok()) throw new Error('Demo login failed');
    const categories = [];
    for (const [name, icon, color] of [['Todos os dias', 'main', '#43BF50'], ['Pequeno-almoço', 'breakfast', '#E9A23B'], ['Vegetariano', 'other', '#36856B']]) {
      categories.push(await request('post', '/categories', { name, icon, color }));
    }
    const examples = [
      ['Massa com tomate e manjericão', 'Uma ideia simples para o jantar, com tomate e ervas frescas.', 10, 20, 0, [['Massa', 320, 'g'], ['Tomate', 500, 'g'], ['Azeite', 2, 'colheres de sopa'], ['Manjericão', 1, 'ramo']], ['Prepara os ingredientes e lava o tomate e o manjericão.', 'Coze a massa de acordo com as instruções da embalagem.', 'Salteia o tomate em azeite até obteres um molho.', 'Envolve a massa no molho e termina com manjericão.']],
      ['Arroz de legumes', 'Um prato de aproveitamento para os dias de semana.', 15, 25, 2, [['Arroz', 250, 'g'], ['Cenoura', 2, 'un.'], ['Ervilhas', 150, 'g']], ['Corta a cenoura em pedaços pequenos.', 'Junta os legumes ao arroz e cozinha com água até ficar tenro.', 'Ajusta os temperos e serve.']],
      ['Sopa de abóbora', 'Uma sopa para preparar de véspera e partilhar à mesa.', 15, 30, 2, [['Abóbora', 600, 'g'], ['Cebola', 1, 'un.'], ['Batata', 200, 'g']], ['Descasca e corta os legumes.', 'Cobre com água e cozinha até ficarem tenros.', 'Tritura e ajusta a consistência.']],
      ['Panquecas de aveia', 'Um pequeno-almoço sem pressa para o fim de semana.', 10, 10, 1, [['Aveia', 120, 'g'], ['Banana', 1, 'un.'], ['Ovos', 2, 'un.']], ['Mistura os ingredientes até obteres uma massa homogénea.', 'Deita pequenas porções numa frigideira antiaderente.', 'Vira cada panqueca e serve.']],
      ['Salada de grão', 'Uma combinação fresca para levar na marmita.', 15, 0, 2, [['Grão cozido', 400, 'g'], ['Tomate', 200, 'g'], ['Pepino', 1, 'un.']], ['Escorre o grão e corta os legumes.', 'Mistura tudo numa taça e tempera a gosto.']],
      ['Legumes assados com alecrim', 'Um tabuleiro de legumes para acompanhar a semana.', 15, 35, 0, [['Batata', 500, 'g'], ['Cenoura', 3, 'un.'], ['Azeite', 2, 'colheres de sopa']], ['Corta os legumes e distribui num tabuleiro.', 'Junta azeite e alecrim.', 'Assa até os legumes estarem tenros, mexendo a meio.']],
    ];
    const recipes = [];
    for (const [title, description, prep_minutes, cook_minutes, category, ingredients, steps] of examples) {
      recipes.push(await request('post', '/recipes', { title, description, prep_minutes, cook_minutes, servings: 4, category_ids: [categories[category].id], notes: 'Exemplo fictício criado para demonstrar a aplicação.', ingredients: ingredients.map(([name, quantity, unit]) => ({ name, quantity, unit })), steps: steps.map((instruction, i) => ({ instruction, duration_minutes: i === 1 ? 10 : null })) }));
    }
    await request('post', `/recipes/${recipes[0].id}/favorite`);
    const now = new Date();
    const monday = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    monday.setUTCDate(monday.getUTCDate() - (monday.getUTCDay() + 6) % 7);
    const day = (offset) => new Date(monday.getTime() + offset * 86400000).toISOString().slice(0, 10);
    for (let i = 0; i < 7; i++) {
      await request('put', `/meal-plan/${day(i)}/almoco`, { recipe_id: recipes[i % recipes.length].id });
      await request('put', `/meal-plan/${day(i)}/jantar`, { recipe_id: recipes[(i + 2) % recipes.length].id });
    }
    await request('put', `/meal-plan/${day(5)}/pequeno_almoco`, { recipe_id: recipes[3].id });
    for (const [name, quantity, unit] of [['Arroz', 1, 'kg'], ['Azeite', 1, 'l'], ['Aveia', 500, 'g']]) await request('post', '/pantry', { name, quantity, unit });
    await request('post', '/shopping-list/generate', { week_start: day(0) });
    const storageState = await context.storageState();
    const errors = [];
    async function capture(ctx, route, name, heading) {
      const page = await ctx.newPage();
      page.on('pageerror', (error) => errors.push(error.message));
      page.on('response', (response) => { if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`); });
      await page.goto(route);
      if (heading) await expect(page.getByRole('heading', { name: heading, exact: true }).first()).toBeVisible();
      await page.waitForLoadState('networkidle');
      await page.evaluate(() => document.fonts.ready);
      if (name === 'mobile-home') await page.getByRole('heading', { name: 'Receitas', exact: true }).evaluate((element) => element.scrollIntoView({ block: 'start' }));
      await page.screenshot({ path: path.join(output, `${name}.png`), animations: 'disabled' });
      console.log(`Captured ${name}`);
      await page.close();
    }
    await capture(context, '/', 'desktop-home', 'Massa com tomate e manjericão');
    await capture(context, '/planeamento', 'desktop-meal-plan');
    const mobile = await browser.newContext({ baseURL, storageState, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, locale: 'pt-PT', timezoneId: 'Europe/Lisbon', colorScheme: 'light' });
    await capture(mobile, '/', 'mobile-home', 'Massa com tomate e manjericão');
    await capture(mobile, '/lista-compras', 'mobile-shopping', 'Lista de compras');
    await capture(mobile, `/receitas/${recipes[0].id}/cozinhar`, 'mobile-cooking');
    const dark = await browser.newContext({ baseURL, storageState, viewport: { width: 1440, height: 1000 }, locale: 'pt-PT', timezoneId: 'Europe/Lisbon', colorScheme: 'dark' });
    await capture(dark, '/', 'desktop-dark', 'Massa com tomate e manjericão');
    if (errors.length) throw new Error(errors.join('\n'));
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
