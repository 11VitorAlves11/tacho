// Creates synthetic examples on a FRESH disposable instance, then captures the real UI.
// See docs/screenshots.md. Never run against an instance containing household data.
const { mkdir, readFile } = require('node:fs/promises');
const path = require('node:path');
const { chromium, expect } = require(process.env.PLAYWRIGHT_MODULE || '@playwright/test');
const baseURL = process.env.SCREENSHOT_BASE_URL || 'http://localhost:18080';
const output = path.resolve(__dirname, '../docs/images');

(async () => {
  await mkdir(output, { recursive: true });
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 1000 }, locale: 'en-GB', timezoneId: 'Europe/Lisbon', colorScheme: 'light' });
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
    for (const [name, icon, color] of [['Everyday meals', 'main', '#43BF50'], ['Breakfast', 'breakfast', '#E9A23B'], ['Vegetarian', 'other', '#36856B']]) {
      categories.push(await request('post', '/categories', { name, icon, color }));
    }
    const examples = [
      ['Tomato and basil pasta', 'An easy dinner with ripe tomatoes and fresh herbs.', 10, 20, 0, [['Pasta', 320, 'g'], ['Tomatoes', 500, 'g'], ['Olive oil', 2, 'tbsp'], ['Basil', 1, 'bunch']], ['Prepare the ingredients and wash the tomatoes and basil.', 'Cook the pasta following the instructions on the packet.', 'Sauté the tomatoes in olive oil until they form a sauce.', 'Toss the pasta in the sauce and finish with fresh basil.']],
      ['Vegetable rice', 'A colourful way to use up vegetables during the week.', 15, 25, 2, [['Rice', 250, 'g'], ['Carrots', 2, 'pcs'], ['Peas', 150, 'g']], ['Dice the carrots into small pieces.', 'Add the vegetables to the rice and simmer with water until tender.', 'Adjust the seasoning and serve.']],
      ['Pumpkin soup', 'A comforting soup to prepare ahead and share at the table.', 15, 30, 2, [['Pumpkin', 600, 'g'], ['Onion', 1, 'pc'], ['Potatoes', 200, 'g']], ['Peel and chop the vegetables.', 'Cover with water and simmer until tender.', 'Blend until smooth and adjust the consistency.']],
      ['Oat pancakes', 'A relaxed breakfast for a slow weekend morning.', 10, 10, 1, [['Oats', 120, 'g'], ['Banana', 1, 'pc'], ['Eggs', 2, 'pcs']], ['Mix the ingredients into a smooth batter.', 'Pour small portions into a non-stick frying pan.', 'Flip each pancake and serve.']],
      ['Chickpea salad', 'A fresh combination to pack for lunch.', 15, 0, 2, [['Cooked chickpeas', 400, 'g'], ['Tomatoes', 200, 'g'], ['Cucumber', 1, 'pc']], ['Drain the chickpeas and chop the vegetables.', 'Mix everything in a bowl and season to taste.']],
      ['Rosemary roasted vegetables', 'A tray of roasted vegetables to enjoy throughout the week.', 15, 35, 0, [['Potatoes', 500, 'g'], ['Carrots', 3, 'pcs'], ['Olive oil', 2, 'tbsp']], ['Chop the vegetables and spread them on a baking tray.', 'Add olive oil and rosemary.', 'Roast until tender, stirring halfway through.']],
    ];
    const recipes = [];
    for (const [title, description, prep_minutes, cook_minutes, category, ingredients, steps] of examples) {
      recipes.push(await request('post', '/recipes', { title, description, prep_minutes, cook_minutes, servings: 4, category_ids: [categories[category].id], notes: 'Fictional example created to demonstrate the app.', ingredients: ingredients.map(([name, quantity, unit]) => ({ name, quantity, unit })), steps: steps.map((instruction, i) => ({ instruction, duration_minutes: i === 1 ? 10 : null })) }));
    }
    const photos = ['pasta', 'rice', 'soup', 'pancakes', 'salad', 'vegetables'];
    for (let index = 0; index < recipes.length; index++) {
      const response = await api.post(`/recipes/${recipes[index].id}/image`, {
        multipart: { file: { name: `${photos[index]}.png`, mimeType: 'image/png', buffer: await readFile(path.join(__dirname, '../docs/recipe-images', `${photos[index]}.png`)) } },
      });
      if (!response.ok()) throw new Error(`Photo upload failed: ${await response.text()}`);
      recipes[index] = await response.json();
      if (!recipes[index].image_path) throw new Error('Recipe cover was not saved');
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
    for (const [name, quantity, unit] of [['Rice', 1, 'kg'], ['Olive oil', 1, 'l'], ['Oats', 500, 'g']]) await request('post', '/pantry', { name, quantity, unit });
    await request('post', '/shopping-list/generate', { week_start: day(0) });
    const errors = [];
    async function capture(ctx, route, name, heading) {
      const page = await ctx.newPage();
      page.on('pageerror', (error) => errors.push(error.message));
      page.on('response', (response) => { if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`); });
      await page.goto(route);
      if (heading) await expect(page.getByRole('heading', { name: heading, exact: true }).first()).toBeVisible();
      await expect(page.locator('html')).toHaveAttribute('lang', 'en');
      await page.waitForLoadState('networkidle');
      await page.evaluate(() => document.fonts.ready);
      await expect.poll(() => page.locator('img').evaluateAll((images) => images.every((image) => image.complete && image.naturalWidth > 0))).toBe(true);
      if (name.endsWith('settings')) {
        await page.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).click();
        await expect(page.getByLabel('Language', { exact: true })).toHaveValue('en');
        await expect(page.locator('html')).toHaveAttribute('lang', 'en');
      }
      if (name === 'mobile-home') await page.getByRole('heading', { name: 'Recipes', exact: true }).evaluate((element) => element.scrollIntoView({ block: 'start' }));
      await page.screenshot({ path: path.join(output, `${name}.png`), animations: 'disabled' });
      console.log(`Captured ${name}`);
      await page.close();
    }
    // Switching language must preserve an in-progress recipe form on desktop.
    const draft = await context.newPage();
    await draft.goto('/adicionar');
    await draft.getByRole('button', { name: 'À mão', exact: true }).click();
    await draft.getByLabel('Título', { exact: true }).fill('Unsaved recipe');
    await draft.getByRole('button', { name: 'Definições', exact: true }).filter({ visible: true }).click();
    await draft.getByLabel('Idioma', { exact: true }).selectOption('en');
    await expect(draft.getByLabel('Title', { exact: true })).toHaveValue('Unsaved recipe');
    await draft.close();
    const storageState = await context.storageState();
    await capture(context, '/', 'desktop-home', 'Tomato and basil pasta');
    await capture(context, '/planeamento', 'desktop-meal-plan');
    await capture(context, `/receitas/${recipes[0].id}`, 'desktop-recipe', 'Tomato and basil pasta');
    const mobile = await browser.newContext({ baseURL, storageState, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, locale: 'en-GB', timezoneId: 'Europe/Lisbon', colorScheme: 'light' });
    await capture(mobile, '/', 'mobile-home', 'Tomato and basil pasta');
    await capture(mobile, '/lista-compras', 'mobile-shopping', 'Shopping list');
    await capture(mobile, `/receitas/${recipes[0].id}/cozinhar`, 'mobile-cooking');
    const dark = await browser.newContext({ baseURL, storageState, viewport: { width: 1440, height: 1000 }, locale: 'en-GB', timezoneId: 'Europe/Lisbon', colorScheme: 'dark' });
    await capture(dark, '/', 'desktop-dark', 'Tomato and basil pasta');
    await capture(mobile, '/', 'mobile-settings', 'Tomato and basil pasta');
    const check = await mobile.newPage();
    await check.goto('/');
    await expect(check.getByRole('heading', { name: 'Recipes', exact: true })).toBeVisible();
    await check.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).click();
    await expect(check.getByLabel('Language', { exact: true })).toHaveValue('en');
    await check.getByLabel('Language', { exact: true }).selectOption('pt-PT');
    await expect(check.getByRole('heading', { name: 'Receitas', exact: true })).toBeVisible();
    await check.getByLabel('Idioma', { exact: true }).selectOption('en');
    await check.reload();
    await expect(check.getByRole('heading', { name: 'Recipes', exact: true })).toBeVisible();
    await check.close();
    console.log('Language switching and persistence verified');
    if (errors.length) throw new Error(errors.join('\n'));
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
