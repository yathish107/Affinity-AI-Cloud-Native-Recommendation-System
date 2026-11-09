"""Real-browser UI tests with explicit API fixtures; no infrastructure required.
python -m pytest frontend/browser-tests/test_frontend_contract.py -q
Install Chromium first: python -m playwright install chromium
These fixtures are test-only and are never shipped as application responses.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import pytest
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = json.loads((ROOT.parent / 'backend/app/catalog.json').read_text())

@pytest.fixture
def ui():
    with sync_playwright() as p:
        options = {'headless': True}
        if os.getenv('CHROMIUM_PATH'):
            options['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors, calls = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        payloads = {
            '/api/products': PRODUCTS,
            '/api/recommendations/student1': {'recommendations': [{**p, 'score': .25, 'explanation': {'reasons': ['Test explanation from API fixture'], 'contributions': {'content': .25}}} for p in PRODUCTS]},
            '/api/trending': PRODUCTS,
            '/api/events/student1': [{'product_id': 'p1', 'event_type': 'click', 'created_at': '2026-01-01T10:00:00Z'}],
            '/api/admin/analytics': {'events': 12, 'processed': 8, 'dead_letters': 1, 'pending': 3, 'users': 2, 'types': {'view': 6, 'click': 4, 'purchase': 2}},
            '/api/system': {'api': 'up', 'database': 'up', 'redis': 'down', 'recommendation': 'up'},
        }
        def route(request):
            uri = urlparse(request.request.url)
            if uri.path.startswith('/api/'):
                calls.append(request.request)
                data = payloads.get(uri.path, {})
                request.fulfill(status=200, content_type='application/json', body=json.dumps(data))
            else:
                name = uri.path.lstrip('/') or 'index.html'
                if name not in ['index.html', 'app.js', 'style.css']:
                    request.fulfill(status=404, body='Not found')
                    return
                mime = {'index.html': 'text/html', 'app.js': 'application/javascript', 'style.css': 'text/css'}[name]
                request.fulfill(status=200, content_type=mime, body=(ROOT/name).read_bytes())
        page.route('**/*', route)
        page.goto('http://localhost:8080/')
        expect(page.locator('#products .card')).to_have_count(12)
        expect(page.locator('#recs .card')).to_have_count(12)
        yield page, calls, errors
        browser.close()


def test_catalogue_and_recommendation_images_search_filter_explanation(ui):
    page, _, errors = ui
    for product in PRODUCTS:
        a = page.locator(f'#products [data-product-id="{product["id"]}"] img')
        b = page.locator(f'#recs [data-product-id="{product["id"]}"] img')
        a.scroll_into_view_if_needed()
        expect(a).to_be_visible()
        page.wait_for_function('(id) => Array.from(document.querySelectorAll(`[data-product-id="${id}"] img`)).filter(i => i.closest("#products")).every(i => i.complete && i.naturalWidth > 0)', arg=product['id'])
        b.scroll_into_view_if_needed()
        page.wait_for_function('(id) => document.querySelector(`#recs [data-product-id="${id}"] img`).naturalWidth > 0', arg=product['id'])
        assert a.get_attribute('src') == b.get_attribute('src')
    page.locator('#search').fill('backpack')
    expect(page.locator('#products .card')).to_have_count(2)
    page.get_by_role('button', name='Fitness', exact=True).click()
    expect(page.locator('#products .card')).to_have_count(1)
    expect(page.locator('#productCount')).to_have_text('1 of 12 products')
    page.locator('#recs summary').first.click()
    expect(page.locator('#recs details').first).to_have_attribute('open', '')
    expect(page.locator('#recs details').first).to_contain_text('Test explanation from API fixture')
    page.locator('#products img').first.evaluate('(img) => img.dispatchEvent(new Event("error"))')
    expect(page.locator('#products')).to_contain_text('Gym BackpackPhotograph unavailable')
    assert not errors


def test_all_pages_and_real_response_fields(ui):
    page, calls, errors = ui
    page.get_by_role('button', name='Click Gaming Laptop', exact=True).first.click()
    expect(page.locator('#message')).to_contain_text('recorded')
    posted = [r.post_data_json for r in calls if r.method == 'POST']
    assert posted[0]['product_id'] == 'p1' and posted[0]['event_type'] == 'click'
    assert posted[0]['event_id'] and posted[0]['user_id'] == 'student1'
    page.get_by_role('button', name='Your Activity', exact=True).click()
    expect(page.locator('#historyRows')).to_contain_text('Gaming Laptop')
    page.locator('#activityType').select_option('purchase')
    expect(page.locator('#historyRows')).to_contain_text('No matching interactions')
    page.get_by_role('button', name='Admin Analytics', exact=True).click()
    page.locator('#adminKey').fill('test-only-key')
    page.locator('#adminLoad').click()
    expect(page.locator('#stats .kpi')).to_have_count(6)
    expect(page.locator('#stats')).to_contain_text('Total events12')
    assert [r for r in calls if '/admin/analytics' in r.url][-1].headers['x-admin-key'] == 'test-only-key'
    page.get_by_role('button', name='System Health', exact=True).click()
    expect(page.locator('#health .up')).to_have_count(3)
    expect(page.locator('#health .down')).to_have_count(1)
    assert not errors


@pytest.mark.parametrize('failure', [400, 404, 500, 'network'])
def test_event_failure_retry_reuses_id(ui, failure):
    page, _, _ = ui
    submitted = []
    def fail(route):
        submitted.append(route.request.post_data_json)
        if failure == 'network': route.abort()
        else: route.fulfill(status=failure, content_type='application/json', body='{"detail":"Test rejection"}')
    page.route('**/api/events', fail)
    action = page.locator('#products').get_by_role('button', name='View Gaming Laptop', exact=True)
    action.click()
    expect(page.locator('#message')).to_contain_text('Request failed')
    expect(page.locator('#message')).not_to_contain_text('recorded')
    def accept(route):
        submitted.append(route.request.post_data_json)
        route.fulfill(status=200, content_type='application/json', body='{}')
    page.route('**/api/events', accept)
    action.click()
    expect(page.locator('#message')).to_contain_text('recorded')
    assert submitted[0] == submitted[1]


@pytest.mark.parametrize('width', [320, 390, 768, 1440])
def test_responsive_all_pages_and_keyboard(ui, width):
    page, _, errors = ui
    page.set_viewport_size({'width': width, 'height': 900})
    for label in ['Discover', 'Your Activity', 'Admin Analytics', 'System Health']:
        page.get_by_role('button', name=label, exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement !== document.body')
    assert not errors


def test_failed_health_check_replaces_green_status_with_unknown(ui):
    page, _, _ = ui
    page.get_by_role('button', name='System Health', exact=True).click()
    expect(page.locator('#health .up')).to_have_count(3)
    page.route('**/api/system', lambda r: r.fulfill(status=500, content_type='application/json', body='{}'))
    page.locator('#systemRefresh').click()
    expect(page.locator('#health .unknown')).to_have_count(4)
    expect(page.locator('#health .up')).to_have_count(0)
    expect(page.locator('#healthUpdated')).to_contain_text('unavailable')
