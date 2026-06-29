// Глобальные переменные
let currentUser = null;
let token = localStorage.getItem('access_token');
const API_BASE = 'https://skillbridge-backend-31qr.onrender.com';

// Показать страницу
async function showPage(page) {
    const content = document.getElementById('page-content');
    const authLinks = document.getElementById('auth-links');
    const userLinks = document.getElementById('user-links');

    if (token) {
        authLinks.style.display = 'none';
        userLinks.style.display = 'inline';
        if (!currentUser) await fetchUser();
    } else {
        authLinks.style.display = 'inline';
        userLinks.style.display = 'none';
    }

    switch (page) {
        case 'home':
            content.innerHTML = await renderHome();
            break;
        case 'register':
            content.innerHTML = renderRegister();
            break;
        case 'login':
            content.innerHTML = renderLogin();
            break;
        case 'profile':
            if (!token) { showPage('login'); return; }
            content.innerHTML = await renderProfile();
            break;
        case 'portfolio':
            if (!token) { showPage('login'); return; }
            content.innerHTML = await renderPortfolio();
            break;
        case 'analysis':
            if (!token) { showPage('login'); return; }
            content.innerHTML = await renderAnalysis();
            break;
        case 'recommendations':
            if (!token) { showPage('login'); return; }
            content.innerHTML = await renderRecommendations();
            break;
        case 'catalog':
            content.innerHTML = await renderCatalog();
            break;
        case 'jobs':
            content.innerHTML = await renderJobs();
            if (token) setTimeout(updateJobsStatus, 300);
            break;
        default:
            content.innerHTML = '<h2>Страница не найдена</h2>';
    }
}

// --- API вызовы ---
async function apiCall(endpoint, method = 'GET', body = null, isFormData = false) {
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isFormData) headers['Content-Type'] = 'application/json';

    const options = { method, headers };
    if (body) {
        options.body = isFormData ? body : JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (!response.ok) {
        if (response.status === 401) {
            localStorage.removeItem('access_token');
            token = null;
            showPage('login');
            throw new Error('Сессия истекла');
        }
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка запроса');
    }
    if (response.status === 204) return null;
    return await response.json();
}

// --- Авторизация ---
async function register(event) {
    event.preventDefault();
    const form = event.target;
    const data = Object.fromEntries(new FormData(form));
    try {
        await apiCall('/auth/register', 'POST', data);
        alert('Регистрация успешна! Теперь войдите.');
        showPage('login');
    } catch (error) {
        alert(error.message);
    }
}

async function login(event) {
    event.preventDefault();
    const form = event.target;
    const data = Object.fromEntries(new FormData(form));
    try {
        const result = await apiCall('/auth/login', 'POST', data);
        token = result.access_token;
        localStorage.setItem('access_token', token);
        await fetchUser();
        showPage('profile');
    } catch (error) {
        alert(error.message);
    }
}

async function logout() {
    localStorage.removeItem('access_token');
    token = null;
    currentUser = null;
    showPage('home');
}

async function fetchUser() {
    try {
        currentUser = await apiCall('/users/me');
        return currentUser;
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
        return null;
    }
}

// --- Профиль ---
async function updateProfile(event) {
    event.preventDefault();
    const form = event.target;
    const data = Object.fromEntries(new FormData(form));
    data.is_public = data.is_public === 'on';
    try {
        await apiCall('/users/me', 'PUT', data);
        alert('Профиль обновлен');
        await fetchUser();
        showPage('profile');
    } catch (error) {
        alert(error.message);
    }
}

async function publishProfile() {
    try {
        await apiCall('/specialists/publish', 'POST');
        alert('Профиль опубликован в каталоге');
        await fetchUser();
        showPage('profile');
    } catch (error) {
        alert(error.message);
    }
}

// --- Портфолио ---
async function uploadPortfolio(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    try {
        await apiCall('/portfolio', 'POST', formData, true);
        alert('Материал загружен');
        showPage('portfolio');
    } catch (error) {
        alert(error.message);
    }
}

async function deletePortfolioItem(id) {
    if (!confirm('Удалить этот материал?')) return;
    try {
        await apiCall(`/portfolio/${id}`, 'DELETE');
        showPage('portfolio');
    } catch (error) {
        alert(error.message);
    }
}

// --- Анализ ---
async function runAnalysis() {
    try {
        await apiCall('/analysis', 'POST');
        alert('Анализ запущен! Результаты появятся ниже.');
        showPage('analysis');
    } catch (error) {
        alert(error.message);
    }
}

async function showCompetencyCard() {
    try {
        const data = await apiCall('/analysis/competencies');
        const cardDiv = document.getElementById('competency-card');
        cardDiv.innerHTML = `
            <div class="analysis-result">
                <h4>Карточка компетенций</h4>
                <p><strong>Сильные стороны:</strong> ${(data.strengths || ['Не определено']).join(', ')}</p>
                <p><strong>Зоны роста:</strong> ${(data.weaknesses || ['Не обнаружено']).join(', ')}</p>
                <p><strong>Рекомендуемые услуги:</strong> ${(data.suggested_services || ['Нет']).join(', ')}</p>
            </div>
        `;
    } catch (error) {
        alert(error.message);
    }
}

// --- Синхронизация вакансий ---
async function syncJobs() {
    const btn = document.getElementById('sync-btn');
    if (!btn) return;
    
    btn.textContent = 'Синхронизация...';
    btn.disabled = true;
    
    try {
        if (!token) {
            alert('Войдите в систему как администратор');
            btn.textContent = 'Обновить вакансии';
            btn.disabled = false;
            return;
        }
        
        const user = await apiCall('/users/me');
        if (user.role !== 'admin') {
            alert('Только администраторы могут обновлять вакансии');
            btn.textContent = 'Обновить вакансии';
            btn.disabled = false;
            return;
        }
        
        const response = await fetch(`${API_BASE}/jobs/sync-hh`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            alert('Синхронизация вакансий запущена! Обновите страницу через минуту.');
            setTimeout(updateJobsStatus, 3000);
        } else {
            const error = await response.json();
            alert('Ошибка: ' + (error.detail || 'Неизвестная ошибка'));
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    } finally {
        btn.textContent = 'Обновить вакансии';
        btn.disabled = false;
    }
}

async function updateJobsStatus() {
    try {
        if (!token) return;
        
        const response = await fetch(`${API_BASE}/jobs/sync-status`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            const totalEl = document.getElementById('total-jobs');
            const hhEl = document.getElementById('hh-jobs');
            const statusEl = document.getElementById('sync-status-text');
            
            if (totalEl) totalEl.textContent = data.total_jobs || 0;
            if (hhEl) hhEl.textContent = data.by_source?.HeadHunter || 0;
            
            if (statusEl) {
                if (data.is_syncing) {
                    statusEl.innerHTML = 'Синхронизация выполняется...';
                    statusEl.className = 'sync-status syncing';
                } else if (data.last_sync) {
                    const lastSync = new Date(data.last_sync).toLocaleString();
                    statusEl.innerHTML = 'Последняя синхронизация: ' + lastSync;
                    statusEl.className = 'sync-status';
                } else {
                    statusEl.innerHTML = 'Синхронизация не выполнялась';
                    statusEl.className = 'sync-status';
                }
            }
        }
    } catch (error) {
        console.error('Ошибка обновления статуса:', error);
    }
}

// --- Рендеринг страниц ---
async function renderHome() {
    return `
        <div class="card" style="text-align: center; padding: 3rem;">
            <h1>Добро пожаловать в SkillBridge Kazakhstan!</h1>
            <p style="font-size: 1.2rem; margin: 1rem 0;">
                Платформа для анализа цифровых навыков, формирования портфолио и поиска возможностей.
            </p>
            <p style="margin: 1rem 0;">Миссия проекта — помочь молодым людям увидеть реальную ценность своих цифровых навыков.</p>
            <div style="margin-top: 2rem;">
                ${!token ? `<button class="btn" onclick="showPage('register')">Начать</button>` : `<button class="btn" onclick="showPage('profile')">Перейти в профиль</button>`}
            </div>
        </div>
        <div class="grid-2">
            <div class="card"><h3>Анализ ИИ</h3><p>Загрузите портфолио и получите анализ ваших навыков с рекомендациями.</p></div>
            <div class="card"><h3>Каталог специалистов</h3><p>Найдите исполнителей для своих задач или опубликуйте свой профиль.</p></div>
            <div class="card"><h3>Агрегатор возможностей</h3><p>Просматривайте вакансии, проектные задачи и фриланс-заказы.</p></div>
            <div class="card"><h3>Рекомендации</h3><p>Получайте персонализированные рекомендации по развитию и трудоустройству.</p></div>
        </div>
    `;
}

function renderRegister() {
    return `
        <div class="card" style="max-width: 500px; margin: 0 auto;">
            <h2>Регистрация</h2>
            <form id="register-form" onsubmit="register(event)">
                <div class="form-group"><label>ФИО</label><input type="text" name="full_name" required></div>
                <div class="form-group"><label>Email</label><input type="email" name="email" required></div>
                <div class="form-group"><label>Пароль (мин. 6 символов)</label><input type="password" name="password" required minlength="6"></div>
                <div class="form-group"><label>Телефон</label><input type="tel" name="phone"></div>
                <div class="form-group"><label>Город</label><input type="text" name="city"></div>
                <button type="submit" class="btn">Зарегистрироваться</button>
            </form>
            <p style="margin-top: 1rem;">Уже есть аккаунт? <a href="#" onclick="showPage('login')">Войти</a></p>
        </div>
    `;
}

function renderLogin() {
    return `
        <div class="card" style="max-width: 400px; margin: 0 auto;">
            <h2>Вход</h2>
            <form id="login-form" onsubmit="login(event)">
                <div class="form-group"><label>Email</label><input type="email" name="email" required></div>
                <div class="form-group"><label>Пароль</label><input type="password" name="password" required></div>
                <button type="submit" class="btn">Войти</button>
            </form>
            <p style="margin-top: 1rem;">Нет аккаунта? <a href="#" onclick="showPage('register')">Зарегистрироваться</a></p>
        </div>
    `;
}

async function renderProfile() {
    if (!currentUser) await fetchUser();
    return `
        <div class="card">
            <h2>Мой профиль</h2>
            <form id="profile-form" onsubmit="updateProfile(event)">
                <div class="form-group"><label>ФИО</label><input type="text" name="full_name" value="${currentUser.full_name || ''}"></div>
                <div class="form-group"><label>Телефон</label><input type="tel" name="phone" value="${currentUser.phone || ''}"></div>
                <div class="form-group"><label>Город</label><input type="text" name="city" value="${currentUser.city || ''}"></div>
                <div class="form-group"><label>О себе (до 500 символов)</label><textarea name="about" maxlength="500">${currentUser.about || ''}</textarea></div>
                <div class="form-group">
                    <label>Уровень опыта</label>
                    <select name="experience_level">
                        <option value="">Выберите</option>
                        <option value="Нет опыта" ${currentUser.experience_level === 'Нет опыта' ? 'selected' : ''}>Нет опыта</option>
                        <option value="Начинающий" ${currentUser.experience_level === 'Начинающий' ? 'selected' : ''}>Начинающий</option>
                        <option value="Средний" ${currentUser.experience_level === 'Средний' ? 'selected' : ''}>Средний</option>
                        <option value="Продвинутый" ${currentUser.experience_level === 'Продвинутый' ? 'selected' : ''}>Продвинутый</option>
                    </select>
                </div>
                <div class="form-group" style="display: flex; align-items: center; gap: 1rem;">
                    <label>Опубликовать профиль в каталоге</label>
                    <input type="checkbox" name="is_public" ${currentUser.is_public ? 'checked' : ''}>
                </div>
                <button type="submit" class="btn">Обновить профиль</button>
            </form>
            <div style="margin-top: 1rem;">
                <button class="btn btn-outline" onclick="publishProfile()">Опубликовать в каталоге</button>
            </div>
        </div>
        <div class="card">
            <h3>Мои навыки</h3>
            <div id="skills-list">${currentUser.skills ? currentUser.skills.map(s => `<span class="skill-tag">${s.skill_name} (${s.level || 'Не указан'})</span>`).join(' ') : 'Навыки не добавлены'}</div>
        </div>
    `;
}

async function renderPortfolio() {
    const portfolioItems = await apiCall('/portfolio');
    return `
        <div class="card">
            <h2>Мое портфолио</h2>
            <form id="portfolio-form" enctype="multipart/form-data" onsubmit="uploadPortfolio(event)">
                <div class="form-group"><label>Название работы</label><input type="text" name="title" required></div>
                <div class="form-group"><label>Описание</label><textarea name="description"></textarea></div>
                <div class="form-group"><label>Категория</label>
                    <select name="category">
                        <option value="design">Дизайн</option>
                        <option value="development">Разработка</option>
                        <option value="video">Видео</option>
                        <option value="smm">SMM</option>
                        <option value="copywriting">Копирайтинг</option>
                        <option value="other">Другое</option>
                    </select>
                </div>
                <div class="form-group"><label>Файл</label><input type="file" name="file" required></div>
                <button type="submit" class="btn">Загрузить</button>
            </form>
        </div>
        <div class="card">
            <h3>Загруженные материалы</h3>
            <div id="portfolio-items">
                ${portfolioItems && portfolioItems.length > 0
        ? portfolioItems.map(item => `
                        <div style="border-bottom: 1px solid #eee; padding: 0.5rem 0;">
                            <strong>${item.title}</strong> (${item.category || 'Без категории'})
                            ${item.is_public ? 'Публичный' : 'Приватный'}
                            <button onclick="deletePortfolioItem('${item.id}')" style="float: right; background: #ef4444; color: white; border: none; padding: 0.3rem 0.8rem; border-radius: 4px; cursor: pointer;">Удалить</button>
                        </div>
                    `).join('')
        : 'Нет загруженных материалов'
    }
            </div>
        </div>
    `;
}

async function renderAnalysis() {
    const analyses = await apiCall('/analysis');
    const latest = analyses && analyses.length > 0 ? analyses[0] : null;
    return `
        <div class="card">
            <h2>Анализ портфолио</h2>
            <button class="btn" onclick="runAnalysis()">Запустить AI-анализ</button>
            ${latest ? `
                <div style="margin-top: 2rem;">
                    <h3>Результаты анализа (${new Date(latest.created_at).toLocaleString()})</h3>
                    <div class="analysis-result">
                        <strong>Сильные стороны:</strong>
                        <ul>${(latest.strengths || ['Не определено']).map(s => `<li>${s}</li>`).join('')}</ul>
                    </div>
                    <div class="analysis-result weakness">
                        <strong>Слабые стороны и пробелы:</strong>
                        <ul>${(latest.weaknesses || ['Не обнаружено']).map(s => `<li>${s}</li>`).join('')}</ul>
                    </div>
                    <div class="analysis-result">
                        <strong>Рекомендации по улучшению:</strong>
                        <ul>${(latest.recommendations || ['Нет рекомендаций']).map(s => `<li>${s}</li>`).join('')}</ul>
                    </div>
                    <div class="analysis-result">
                        <strong>Рекомендуемые услуги:</strong>
                        <ul>${(latest.suggested_services || ['Нет предложений']).map(s => `<li>${s}</li>`).join('')}</ul>
                    </div>
                </div>
            ` : '<p>Анализ еще не проведен. Нажмите кнопку выше.</p>'}
        </div>
        <div class="card">
            <h3>Карточка компетенций</h3>
            <button class="btn btn-outline" onclick="showCompetencyCard()">Показать карточку компетенций</button>
            <div id="competency-card"></div>
        </div>
    `;
}

async function renderRecommendations() {
    const recs = await apiCall('/jobs/recommended');
    return `
        <div class="card">
            <h2>Рекомендованные вакансии и задачи</h2>
            ${recs && recs.length > 0
        ? recs.map(rec => `
                    <div style="border-bottom: 1px solid #eee; padding: 1rem 0;">
                        <h3>${rec.job.title}</h3>
                        <p><strong>Компания:</strong> ${rec.job.company || 'Не указана'}</p>
                        <p><strong>Описание:</strong> ${rec.job.description || 'Нет описания'}</p>
                        <p><strong>Местоположение:</strong> ${rec.job.location || 'Не указано'}</p>
                        <p><strong>Тип занятости:</strong> ${rec.job.employment_type || 'Не указан'}</p>
                        <p><strong>Релевантность:</strong> ${Math.round((rec.relevance_score || 0) * 100)}%</p>
                        ${rec.job.link ? `<a href="${rec.job.link}" target="_blank" class="btn">Подробнее</a>` : ''}
                    </div>
                `).join('')
        : 'Нет рекомендаций. Запустите анализ портфолио или добавьте больше навыков.'
    }
        </div>
    `;
}

async function renderCatalog() {
    const specialists = await apiCall('/specialists');
    return `
        <div class="card">
            <h2>Каталог специалистов</h2>
            <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;">
                <input type="text" placeholder="Поиск по городу..." id="city-filter" onchange="filterCatalog()">
                <select id="level-filter" onchange="filterCatalog()">
                    <option value="">Все уровни</option>
                    <option value="Начинающий">Начинающий</option>
                    <option value="Средний">Средний</option>
                    <option value="Продвинутый">Продвинутый</option>
                </select>
                <button class="btn" onclick="filterCatalog()">Применить</button>
            </div>
            <div id="catalog-list">
                ${specialists && specialists.length > 0
        ? specialists.map(user => `
                        <div style="border-bottom: 1px solid #eee; padding: 1rem 0;">
                            <h3>${user.full_name}</h3>
                            <p><strong>Город:</strong> ${user.city || 'Не указан'}</p>
                            <p><strong>Уровень:</strong> ${user.experience_level || 'Не указан'}</p>
                            <p><strong>О себе:</strong> ${user.about || 'Нет описания'}</p>
                            <button class="btn btn-outline" onclick="viewSpecialist('${user.id}')">Посмотреть профиль</button>
                        </div>
                    `).join('')
        : 'Нет опубликованных профилей'
    }
            </div>
        </div>
    `;
}

async function renderJobs() {
    try {
        const jobs = await apiCall('/jobs');
        
        let statusHTML = '';
        if (token) {
            statusHTML = `
                <div id="sync-status-container">
                    <div id="sync-status-text" class="sync-status">Загрузка статуса...</div>
                    <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem;">
                        <div>
                            <strong>Всего вакансий:</strong> <span id="total-jobs">0</span>
                            (HeadHunter: <span id="hh-jobs">0</span>)
                        </div>
                        <button class="btn btn-success" id="sync-btn" onclick="syncJobs()">
                            Обновить вакансии
                        </button>
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="card">
                <h2>Вакансии и задачи</h2>
                ${statusHTML}
                <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;">
                    <input type="text" placeholder="Поиск по ключевым словам..." id="job-search" 
                           oninput="filterJobs()" style="flex: 1; padding: 0.7rem; border: 1px solid #ddd; border-radius: 8px;">
                    <select id="job-category-filter" onchange="filterJobs()">
                        <option value="">Все категории</option>
                        <option value="development">Разработка</option>
                        <option value="design">Дизайн</option>
                        <option value="smm">SMM</option>
                        <option value="video">Видео</option>
                        <option value="copywriting">Копирайтинг</option>
                        <option value="analytics">Аналитика</option>
                        <option value="project_management">Управление проектами</option>
                        <option value="quality_assurance">Тестирование</option>
                        <option value="devops">DevOps</option>
                        <option value="hr">HR</option>
                        <option value="sales">Продажи</option>
                        <option value="finance">Финансы</option>
                        <option value="legal">Юриспруденция</option>
                    </select>
                    <button class="btn" onclick="filterJobs()">Применить</button>
                </div>
                <div id="jobs-list">
                    ${jobs && jobs.length > 0 
                        ? jobs.map(job => {
                            const employmentClass = job.employment_type || 'full_time';
                            const categoryLabels = {
                                'development': 'Разработка',
                                'design': 'Дизайн',
                                'smm': 'SMM',
                                'video': 'Видео',
                                'copywriting': 'Копирайтинг',
                                'analytics': 'Аналитика',
                                'project_management': 'Управление проектами',
                                'quality_assurance': 'Тестирование',
                                'devops': 'DevOps',
                                'hr': 'HR',
                                'sales': 'Продажи',
                                'finance': 'Финансы',
                                'legal': 'Юриспруденция'
                            };
                            const categoryLabel = categoryLabels[job.category] || 'Другое';
                            
                            return `
                                <div class="job-card" data-category="${job.category || ''}" data-title="${job.title || ''}" data-company="${job.company || ''}">
                                    <h3>${categoryLabel}: ${job.title}</h3>
                                    <p><strong>Компания:</strong> ${job.company || 'Не указана'}</p>
                                    <p><strong>Описание:</strong> ${job.description ? job.description.substring(0, 200) + '...' : 'Нет описания'}</p>
                                    <p><strong>Местоположение:</strong> ${job.location || 'Не указано'}</p>
                                    <p>
                                        <span class="job-tag ${employmentClass}">${employmentClass.replace('_', ' ')}</span>
                                        <span class="job-tag office">${job.source || 'Не указан'}</span>
                                    </p>
                                    ${job.link ? `<a href="${job.link}" target="_blank" class="btn" style="margin-top: 0.5rem;">Подробнее</a>` : ''}
                                </div>
                            `;
                        }).join('')
                        : 'Нет доступных вакансий. Нажмите "Обновить вакансии", чтобы загрузить их с HeadHunter.'
                    }
                </div>
            </div>
        `;
    } catch (error) {
        return `<div class="card"><p>Ошибка загрузки вакансий: ${error.message}</p></div>`;
    }
}

// --- Фильтрация ---
function filterCatalog() {
    const city = document.getElementById('city-filter').value.toLowerCase();
    const level = document.getElementById('level-filter').value;
    const items = document.querySelectorAll('#catalog-list > div');
    items.forEach(item => {
        const text = item.innerText.toLowerCase();
        const showCity = !city || text.includes(city);
        const showLevel = !level || text.includes(level);
        item.style.display = (showCity && showLevel) ? 'block' : 'none';
    });
}

function filterJobs() {
    const search = document.getElementById('job-search')?.value.toLowerCase() || '';
    const category = document.getElementById('job-category-filter')?.value || '';
    const items = document.querySelectorAll('#jobs-list .job-card');
    
    items.forEach(item => {
        const title = item.dataset.title?.toLowerCase() || '';
        const company = item.dataset.company?.toLowerCase() || '';
        const itemCategory = item.dataset.category || '';
        
        const matchesSearch = !search || title.includes(search) || company.includes(search);
        const matchesCategory = !category || itemCategory === category;
        
        item.style.display = (matchesSearch && matchesCategory) ? 'block' : 'none';
    });
}

// --- Просмотр специалиста ---
async function viewSpecialist(id) {
    try {
        const user = await apiCall(`/specialists/${id}`);
        alert(`Профиль ${user.full_name}:\nГород: ${user.city || 'Не указан'}\nУровень: ${user.experience_level || 'Не указан'}\nО себе: ${user.about || 'Нет описания'}`);
    } catch (error) {
        alert(error.message);
    }
}

// --- Инициализация ---
document.addEventListener('DOMContentLoaded', () => {
    showPage('home');
});